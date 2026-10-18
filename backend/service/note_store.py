# -*- coding: utf-8 -*-
"""
个人笔记存储（SQLite）

保存时用 nh3 做 HTML sanitize：
- 白名单标签（安全子集）保留
- <script>/<iframe>/<style>/on* 事件属性全部移除
- href/src 只允许 http/https/mailto，阻断 javascript: 协议

作者：@zlxaaa
创建日期：2026-10-18
版本：1.1.0（放宽白名单到安全 HTML 子集）
"""

from datetime import datetime

import nh3

from core import db
from utils.mlnlog import MLN_LOG_EXCEPTION


# 保留的安全 HTML 标签（Markdown 渲染常见 + 少量排版增强）
ALLOWED_TAGS = {
    "a", "abbr", "b", "blockquote", "br", "code", "del", "details",
    "div", "em", "h1", "h2", "h3", "h4", "h5", "h6", "hr", "i",
    "img", "ins", "kbd", "li", "mark", "ol", "p", "pre", "q",
    "rp", "rt", "ruby", "s", "small", "span", "strike", "strong",
    "sub", "summary", "sup", "table", "tbody", "td", "tfoot", "th",
    "thead", "tr", "u", "ul",
}

# 每个标签允许的属性（"*" 表示所有标签通用的属性）
ALLOWED_ATTRS = {
    "*": {"class"},
    "a": {"href", "title", "target"},
    "img": {"src", "alt", "title", "width", "height"},
    "code": {"class"},
    "pre": {"class"},
    "span": {"class"},
    "div": {"class"},
    "td": {"colspan", "rowspan"},
    "th": {"colspan", "rowspan"},
}

# 链接/图片协议白名单，挡掉 javascript: data: 等
ALLOWED_URL_SCHEMES = {"http", "https", "mailto"}


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _sanitize_md(md: str) -> str:
    """白名单 sanitize；保留 Markdown 源文本和安全 HTML 子集。"""
    try:
        return nh3.clean(
            md or "",
            tags=ALLOWED_TAGS,
            attributes=ALLOWED_ATTRS,
            url_schemes=ALLOWED_URL_SCHEMES,
        )
    except Exception as e:
        MLN_LOG_EXCEPTION("Markdown sanitize 失败：%s", e)
        return md or ""


def _row(row) -> dict:
    return dict(row) if row else None


def create(user_id: int, title: str | None, content_md: str,
           class_key: str | None, visibility: str = "private") -> int:
    content_md = _sanitize_md(content_md)
    now = _now()
    conn = db.get_conn()
    with conn:
        cur = conn.execute(
            "INSERT INTO notes (user_id, title, content_md, class_key, visibility, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (user_id, title, content_md, class_key, visibility, now, now),
        )
    return cur.lastrowid


def update(note_id: int, user_id: int, title: str | None, content_md: str,
           class_key: str | None, visibility: str) -> bool:
    content_md = _sanitize_md(content_md)
    conn = db.get_conn()
    with conn:
        cur = conn.execute(
            "UPDATE notes SET title=?, content_md=?, class_key=?, visibility=?, updated_at=? "
            "WHERE id=? AND user_id=?",
            (title, content_md, class_key, visibility, _now(), note_id, user_id),
        )
    return cur.rowcount > 0


def get_one(note_id: int, user_id: int | None = None) -> dict | None:
    conn = db.get_conn()
    if user_id is not None:
        row = conn.execute(
            "SELECT * FROM notes WHERE id=? AND user_id=?", (note_id, user_id)
        ).fetchone()
    else:
        row = conn.execute("SELECT * FROM notes WHERE id=?", (note_id,)).fetchone()
    return _row(row)


def get_public(note_id: int) -> dict | None:
    row = db.get_conn().execute(
        "SELECT n.*, u.username FROM notes n JOIN users u ON n.user_id = u.id "
        "WHERE n.id=? AND n.visibility='public'", (note_id,)
    ).fetchone()
    return _row(row)


def list_mine(user_id: int, page: int = 1, page_size: int = 20, q: str = "") -> dict:
    conn = db.get_conn()
    where = "WHERE user_id=?"
    args = [user_id]
    if q:
        where += " AND (IFNULL(title,'') LIKE ? OR content_md LIKE ?)"
        kw = f"%{q}%"
        args.extend([kw, kw])
    total = conn.execute(f"SELECT COUNT(*) FROM notes {where}", args).fetchone()[0]
    offset = (page - 1) * page_size
    rows = conn.execute(
        f"SELECT * FROM notes {where} ORDER BY id DESC LIMIT ? OFFSET ?",
        args + [page_size, offset],
    ).fetchall()
    return {"items": [_row(r) for r in rows], "total": total,
            "page": page, "page_size": page_size}


def list_public(page: int = 1, page_size: int = 20, q: str = "") -> dict:
    conn = db.get_conn()
    where = "WHERE n.visibility='public'"
    args = []
    if q:
        where += " AND (IFNULL(n.title,'') LIKE ? OR n.content_md LIKE ?)"
        kw = f"%{q}%"
        args.extend([kw, kw])
    total = conn.execute(f"SELECT COUNT(*) FROM notes n {where}", args).fetchone()[0]
    offset = (page - 1) * page_size
    rows = conn.execute(
        f"SELECT n.*, u.username FROM notes n JOIN users u ON n.user_id = u.id "
        f"{where} ORDER BY n.id DESC LIMIT ? OFFSET ?",
        args + [page_size, offset],
    ).fetchall()
    return {"items": [_row(r) for r in rows], "total": total,
            "page": page, "page_size": page_size}


def delete(note_id: int, user_id: int) -> bool:
    conn = db.get_conn()
    with conn:
        cur = conn.execute("DELETE FROM notes WHERE id=? AND user_id=?", (note_id, user_id))
    return cur.rowcount > 0


def set_visibility(note_id: int, user_id: int, visibility: str) -> bool:
    if visibility not in ("private", "public"):
        raise ValueError("visibility 只能是 private / public")
    conn = db.get_conn()
    row = conn.execute(
        "SELECT visibility FROM notes WHERE id=? AND user_id=?", (note_id, user_id)
    ).fetchone()
    if not row:
        return False
    if row["visibility"] == "admin_hidden" and visibility == "public":
        raise PermissionError("该笔记已被管理员隐藏，不能自行重新公开")
    with conn:
        conn.execute(
            "UPDATE notes SET visibility=?, updated_at=? WHERE id=? AND user_id=?",
            (visibility, _now(), note_id, user_id),
        )
    return True


def admin_hide(note_id: int) -> bool:
    conn = db.get_conn()
    with conn:
        cur = conn.execute(
            "UPDATE notes SET visibility='admin_hidden', updated_at=? WHERE id=?",
            (_now(), note_id),
        )
    return cur.rowcount > 0


def list_hidden(page: int = 1, page_size: int = 20) -> dict:
    """管理员用：列出所有 admin_hidden 笔记。"""
    conn = db.get_conn()
    total = conn.execute(
        "SELECT COUNT(*) FROM notes WHERE visibility='admin_hidden'"
    ).fetchone()[0]
    offset = (page - 1) * page_size
    rows = conn.execute(
        "SELECT n.*, u.username FROM notes n JOIN users u ON n.user_id = u.id "
        "WHERE n.visibility='admin_hidden' ORDER BY n.id DESC LIMIT ? OFFSET ?",
        (page_size, offset),
    ).fetchall()
    return {"items": [_row(r) for r in rows], "total": total,
            "page": page, "page_size": page_size}


def admin_unhide(note_id: int) -> bool:
    """管理员解除隐藏：改回 private，是否重新公开由用户自行决定。"""
    conn = db.get_conn()
    with conn:
        cur = conn.execute(
            "UPDATE notes SET visibility='private', updated_at=? "
            "WHERE id=? AND visibility='admin_hidden'",
            (_now(), note_id),
        )
    return cur.rowcount > 0