# -*- coding: utf-8 -*-
"""
管理员审计日志

记录管理员对用户的关键操作：添加用户、禁用/启用、重置密码、
后续阶段的隐藏公开内容。不记录密码与 token。

作者：@zlxaaa
创建日期：2026-10-18
版本：1.0.0
"""

import json
from datetime import datetime

from core import db


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def write(admin_id: int, action: str,
          target_user: int = None,
          target_type: str = None,
          target_id: int = None,
          detail: dict = None) -> None:
    conn = db.get_conn()
    with conn:
        conn.execute(
            "INSERT INTO admin_audit "
            "(admin_id, action, target_user, target_type, target_id, detail_json, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                admin_id, action, target_user, target_type, target_id,
                json.dumps(detail, ensure_ascii=False) if detail else None,
                _now(),
            ),
        )


def list_audit(page: int = 1, page_size: int = 20) -> dict:
    conn = db.get_conn()
    offset = (page - 1) * page_size
    total = conn.execute("SELECT COUNT(*) FROM admin_audit").fetchone()[0]
    rows = conn.execute(
        "SELECT a.*, u.username AS admin_name "
        "FROM admin_audit a LEFT JOIN users u ON a.admin_id = u.id "
        "ORDER BY a.id DESC LIMIT ? OFFSET ?",
        (page_size, offset),
    ).fetchall()
    items = []
    for r in rows:
        d = dict(r)
        if d.get("detail_json"):
            try:
                d["detail"] = json.loads(d["detail_json"])
            except Exception:
                d["detail"] = None
        d.pop("detail_json", None)
        items.append(d)
    return {"items": items, "total": total, "page": page, "page_size": page_size}