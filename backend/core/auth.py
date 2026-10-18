# -*- coding: utf-8 -*-
"""
认证核心：密码哈希、token 签发/校验、FastAPI 依赖。

- 密码：PBKDF2-HMAC-SHA256，每用户独立随机盐，迭代参数随记录存储。
- token：随机 32 字节 URL-safe 字符串，内存字典保存，重启即失效。
- 依赖：require_user / require_admin 供路由直接 Depends。

作者：
    @zlxaaa

创建日期：2026-10-18
版本：1.0.0

许可证：内部使用，未经许可不得传播。
"""

import hashlib
import hmac
import secrets
import threading
import time
from typing import Optional

from fastapi import Depends, Header, HTTPException

from core.config import TOKEN_TTL_HOURS

PBKDF2_ALGO = "sha256"
PBKDF2_ITER = 200_000
SALT_BYTES = 16
HASH_BYTES = 32

_tokens_lock = threading.Lock()
_tokens: dict[str, dict] = {}


def hash_password(password: str) -> dict:
    salt = secrets.token_bytes(SALT_BYTES)
    dk = hashlib.pbkdf2_hmac(
        PBKDF2_ALGO, password.encode("utf-8"), salt, PBKDF2_ITER, HASH_BYTES
    )
    return {
        "algo": PBKDF2_ALGO,
        "iterations": PBKDF2_ITER,
        "salt": salt.hex(),
        "pwd_hash": dk.hex(),
    }


def verify_password(password: str, record: dict) -> bool:
    try:
        salt = bytes.fromhex(record["salt"])
        expected = bytes.fromhex(record["pwd_hash"])
        dk = hashlib.pbkdf2_hmac(
            record.get("algo", PBKDF2_ALGO),
            password.encode("utf-8"),
            salt,
            int(record.get("iterations", PBKDF2_ITER)),
            len(expected),
        )
        return hmac.compare_digest(dk, expected)
    except (KeyError, ValueError, TypeError):
        return False


def issue_token(user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    with _tokens_lock:
        _tokens[token] = {
            "user_id": user_id,
            "exp": time.time() + TOKEN_TTL_HOURS * 3600,
        }
    return token


def revoke_token(token: str) -> bool:
    with _tokens_lock:
        return _tokens.pop(token, None) is not None


def resolve_token(token: str) -> Optional[dict]:
    with _tokens_lock:
        info = _tokens.get(token)
        if not info:
            return None
        if info["exp"] < time.time():
            _tokens.pop(token, None)
            return None
        return info


def extract_bearer(authorization: Optional[str]) -> Optional[str]:
    if not authorization:
        return None
    parts = authorization.split(" ", 1)
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1].strip()
    return None


def require_user(authorization: Optional[str] = Header(None)) -> dict:
    from service.user_store import get_user_by_id

    token = extract_bearer(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="未登录")
    info = resolve_token(token)
    if not info:
        raise HTTPException(status_code=401, detail="登录已过期，请重新登录")
    user = get_user_by_id(info["user_id"])
    if not user or user.get("disabled"):
        raise HTTPException(status_code=401, detail="账号不可用")
    return user


def require_admin(user: dict = Depends(require_user)) -> dict:
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return user

def optional_user(authorization: str | None = Header(None)) -> dict | None:
    """不阻断未登录；有有效 token 则返回 user，否则 None。"""
    if not authorization:
        return None
    token = extract_bearer(authorization)
    if not token:
        return None
    info = resolve_token(token)
    if not info:
        return None
    from service.user_store import get_user_by_id
    u = get_user_by_id(info["user_id"])
    if not u or u.get("disabled"):
        return None
    return u