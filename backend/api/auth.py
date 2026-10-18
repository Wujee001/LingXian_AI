# -*- coding: utf-8 -*-
"""
认证路由：/api/auth/login · logout · me

响应统一 {"success": True, "data": ...}。

作者：
    @zlxaaa

创建日期：2026-10-18
版本：1.0.0
"""

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel

from core.auth import (
    extract_bearer,
    issue_token,
    require_user,
    revoke_token,
)
from service.user_store import authenticate
from utils.mlnlog import MLN_LOG_INFO, MLN_LOG_WARN

router = APIRouter()


class LoginReq(BaseModel):
    username: str
    password: str


@router.post("/login")
def login(req: LoginReq):
    user = authenticate(req.username, req.password)
    if not user:
        MLN_LOG_WARN("登录失败：%s", req.username)
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    token = issue_token(user["id"])
    MLN_LOG_INFO("登录成功：%s (id=%d)", user["username"], user["id"])
    return {"success": True, "data": {"token": token, "user": user}}


@router.post("/logout")
def logout(authorization: str = Header(None)):
    token = extract_bearer(authorization)
    if token:
        revoke_token(token)
    return {"success": True}


@router.get("/me")
def me(user: dict = Depends(require_user)):
    return {"success": True, "data": {"user": user}}