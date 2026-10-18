# -*- coding: utf-8 -*-
"""
用户表访问层（SQLite）

对外返回的 user dict 永远剔除 salt / pwd_hash。
authenticate 内置假哈希，避免用户名枚举时序差。

作者：
    @zlxaaa

创建日期：2026-10-18
版本：1.0.0

许可证：内部使用，未经许可不得传播。
"""

import sqlite3
from datetime import datetime
from typing import Optional

from core import db
from core.auth import hash_password, verify_password
from utils.mlnlog import MLN_LOG_INFO, MLN_LOG_EXCEPTION


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _public(row: Optional[sqlite3.Row]) -> Optional[dict]:
    if row is None:
        return None
    d = dict(row)
    d.pop("salt", None)
    d.pop("pwd_hash", None)
    d["disabled"] = bool(d.get("disabled"))
    return d


def create_user(username: str, password: str, role: str = "user") -> int:
    if role not in ("admin", "user"):
        raise ValueError("role 必须是 admin 或 user")
    rec = hash_password(password)
    conn = db.get_conn()
    try:
        with conn:
            cur = conn.execute(
                "INSERT INTO users (username, algo, iterations, salt, pwd_hash, role, disabled, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, 0, ?)",
                (username, rec["algo"], rec["iterations"], rec["salt"],
                 rec["pwd_hash"], role, _now()),
            )
        MLN_LOG_INFO("用户已创建：%s (role=%s, id=%d)", username, role, cur.lastrowid)
        return cur.lastrowid
    except sqlite3.IntegrityError as e:
        MLN_LOG_EXCEPTION("创建用户失败（可能重名）：%s -> %s", username, e)
        raise ValueError(f"用户名已存在：{username}")


def get_user_by_id(user_id: int) -> Optional[dict]:
    row = db.get_conn().execute(
        "SELECT * FROM users WHERE id = ?", (user_id,)
    ).fetchone()
    return _public(row)


def get_user_raw(username: str) -> Optional[dict]:
    """内部使用：包含 salt/pwd_hash，仅供 authenticate 校验。"""
    row = db.get_conn().execute(
        "SELECT * FROM users WHERE username = ?", (username,)
    ).fetchone()
    return dict(row) if row else None


def list_users() -> list[dict]:
    rows = db.get_conn().execute(
        "SELECT * FROM users ORDER BY id ASC"
    ).fetchall()
    return [_public(r) for r in rows]


def authenticate(username: str, password: str) -> Optional[dict]:
    raw = get_user_raw(username)
    if not raw:
        # 假哈希，抗用户名枚举时序差
        hash_password(password)
        return None
    if not verify_password(password, raw):
        return None
    if raw.get("disabled"):
        return None
    return _public(dict(raw) if not isinstance(raw, sqlite3.Row) else raw)


def reset_password(user_id: int, password: str) -> None:
    rec = hash_password(password)
    conn = db.get_conn()
    with conn:
        cur = conn.execute(
            "UPDATE users SET algo=?, iterations=?, salt=?, pwd_hash=? WHERE id=?",
            (rec["algo"], rec["iterations"], rec["salt"], rec["pwd_hash"], user_id),
        )
    if cur.rowcount == 0:
        raise ValueError(f"用户不存在：id={user_id}")


def set_disabled(user_id: int, disabled: bool) -> None:
    conn = db.get_conn()
    with conn:
        cur = conn.execute(
            "UPDATE users SET disabled = ? WHERE id = ?",
            (1 if disabled else 0, user_id),
        )
    if cur.rowcount == 0:
        raise ValueError(f"用户不存在：id={user_id}")


def ensure_seed_admin(username: str, password: str) -> bool:
    """首次启动预置账号；已存在则不覆盖。返回是否新建。"""
    row = db.get_conn().execute(
        "SELECT id FROM users WHERE username = ?", (username,)
    ).fetchone()
    if row:
        return False
    create_user(username, password, role="admin")
    return True