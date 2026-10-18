# -*- coding: utf-8 -*-
"""
历史记录存储（SQLite + 文件快照）

提供 single/sheet 两类历史的写入、列表、详情、删除、可见性切换。
写入时同步复制快照图到 data/history_images/{user_id}/。

作者：@zlxaaa
创建日期：2026-10-18
版本：1.0.0
"""

import json
from datetime import datetime

from core import db
from service import image_store
from utils.mlnlog import MLN_LOG_EXCEPTION, MLN_LOG_INFO


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _url(rel: str | None) -> str | None:
    return f"/history_images/{rel}" if rel else None


def _row_to_dict(row) -> dict:
    d = dict(row)
    if d.get("parse_json"):
        try:
            d["parse"] = json.loads(d["parse_json"])
        except Exception:
            d["parse"] = None
    d.pop("parse_json", None)
    d["image_url"] = _url(d.get("image_path"))
    d["thumb_url"] = _url(d.get("thumb_path"))
    return d


def write_single(user_id: int, query_key: str | None, parse_payload: dict, pil_image) -> int | None:
    try:
        saved = image_store.save_from_pil(pil_image, user_id)
        image_path, thumb_path = saved if saved else (None, None)
        parse_json = json.dumps(parse_payload, ensure_ascii=False)
        conn = db.get_conn()
        with conn:
            cur = conn.execute(
                "INSERT INTO history "
                "(user_id, query_type, query_key, parse_json, image_path, thumb_path, visibility, created_at) "
                "VALUES (?, 'single', ?, ?, ?, ?, 'private', ?)",
                (user_id, query_key, parse_json, image_path, thumb_path, _now()),
            )
        MLN_LOG_INFO("历史写入（single）：user=%d key=%s id=%d", user_id, query_key, cur.lastrowid)
        return cur.lastrowid
    except Exception as e:
        MLN_LOG_EXCEPTION("历史写入失败（single）：%s", e)
        return None


def write_sheet(user_id: int, source_path: str, data: dict) -> int | None:
    """data 是 whole_sheet 接口返回的 data 段整体快照。"""
    try:
        image_url = data.get("image_url") or ""
        ext = "." + image_url.rsplit(".", 1)[-1].lower() if "." in image_url else ".png"
        saved = image_store.save_from_file(source_path, user_id, ext=ext)
        image_path, thumb_path = saved if saved else (None, None)
        parse_json = json.dumps(data, ensure_ascii=False)
        conn = db.get_conn()
        with conn:
            cur = conn.execute(
                "INSERT INTO history "
                "(user_id, query_type, query_key, parse_json, image_path, thumb_path, visibility, created_at) "
                "VALUES (?, 'sheet', NULL, ?, ?, ?, 'private', ?)",
                (user_id, parse_json, image_path, thumb_path, _now()),
            )
        MLN_LOG_INFO("历史写入（sheet）：user=%d items=%d id=%d",
                     user_id, len(data.get("items") or []), cur.lastrowid)
        return cur.lastrowid
    except Exception as e:
        MLN_LOG_EXCEPTION("历史写入失败（sheet）：%s", e)
        return None


def list_mine(user_id: int, page: int = 1, page_size: int = 20, q: str = "") -> dict:
    conn = db.get_conn()
    where = "WHERE user_id = ?"
    args = [user_id]
    if q:
        where += " AND (IFNULL(query_key,'') LIKE ? OR parse_json LIKE ?)"
        kw = f"%{q}%"
        args.extend([kw, kw])
    total = conn.execute(f"SELECT COUNT(*) FROM history {where}", args).fetchone()[0]
    offset = (page - 1) * page_size
    rows = conn.execute(
        f"SELECT * FROM history {where} ORDER BY id DESC LIMIT ? OFFSET ?",
        args + [page_size, offset],
    ).fetchall()
    return {
        "items": [_row_to_dict(r) for r in rows],
        "total": total, "page": page, "page_size": page_size,
    }


def get_one(history_id: int, user_id: int) -> dict | None:
    row = db.get_conn().execute(
        "SELECT * FROM history WHERE id = ? AND user_id = ?",
        (history_id, user_id),
    ).fetchone()
    return _row_to_dict(row) if row else None


def delete(history_id: int, user_id: int) -> bool:
    conn = db.get_conn()
    row = conn.execute(
        "SELECT image_path, thumb_path FROM history WHERE id = ? AND user_id = ?",
        (history_id, user_id),
    ).fetchone()
    if not row:
        return False
    with conn:
        conn.execute("DELETE FROM history WHERE id = ? AND user_id = ?",
                     (history_id, user_id))
    image_store.delete(row["image_path"], row["thumb_path"])
    MLN_LOG_INFO("历史删除：id=%d user=%d", history_id, user_id)
    return True


def set_visibility(history_id: int, user_id: int, visibility: str) -> bool:
    if visibility not in ("private", "public"):
        raise ValueError("visibility 只能是 private / public")
    conn = db.get_conn()
    row = conn.execute(
        "SELECT visibility FROM history WHERE id = ? AND user_id = ?",
        (history_id, user_id),
    ).fetchone()
    if not row:
        return False
    if row["visibility"] == "admin_hidden" and visibility == "public":
        raise PermissionError("该记录已被管理员隐藏，不能自行重新公开")
    with conn:
        conn.execute("UPDATE history SET visibility = ? WHERE id = ? AND user_id = ?",
                     (visibility, history_id, user_id))
    return True

def list_public(page: int = 1, page_size: int = 20, q: str = "") -> dict:
    conn = db.get_conn()
    where = "WHERE h.visibility='public'"
    args = []
    if q:
        where += " AND (IFNULL(h.query_key,'') LIKE ? OR h.parse_json LIKE ?)"
        kw = f"%{q}%"
        args.extend([kw, kw])
    total = conn.execute(f"SELECT COUNT(*) FROM history h {where}", args).fetchone()[0]
    offset = (page - 1) * page_size
    rows = conn.execute(
        f"SELECT h.*, u.username FROM history h JOIN users u ON h.user_id = u.id "
        f"{where} ORDER BY h.id DESC LIMIT ? OFFSET ?",
        args + [page_size, offset],
    ).fetchall()
    return {"items": [_row_to_dict(r) for r in rows], "total": total,
            "page": page, "page_size": page_size}


def get_public(history_id: int) -> dict | None:
    row = db.get_conn().execute(
        "SELECT h.*, u.username FROM history h JOIN users u ON h.user_id = u.id "
        "WHERE h.id=? AND h.visibility='public'", (history_id,)
    ).fetchone()
    return _row_to_dict(row) if row else None


def admin_hide(history_id: int) -> bool:
    conn = db.get_conn()
    with conn:
        cur = conn.execute(
            "UPDATE history SET visibility='admin_hidden' WHERE id=?", (history_id,)
        )
    return cur.rowcount > 0


def list_hidden(page: int = 1, page_size: int = 20) -> dict:
    """管理员用：列出所有 admin_hidden 历史。"""
    conn = db.get_conn()
    total = conn.execute(
        "SELECT COUNT(*) FROM history WHERE visibility='admin_hidden'"
    ).fetchone()[0]
    offset = (page - 1) * page_size
    rows = conn.execute(
        "SELECT h.*, u.username FROM history h JOIN users u ON h.user_id = u.id "
        "WHERE h.visibility='admin_hidden' ORDER BY h.id DESC LIMIT ? OFFSET ?",
        (page_size, offset),
    ).fetchall()
    return {"items": [_row_to_dict(r) for r in rows], "total": total,
            "page": page, "page_size": page_size}


def admin_unhide(history_id: int) -> bool:
    conn = db.get_conn()
    with conn:
        cur = conn.execute(
            "UPDATE history SET visibility='private' "
            "WHERE id=? AND visibility='admin_hidden'",
            (history_id,),
        )
    return cur.rowcount > 0