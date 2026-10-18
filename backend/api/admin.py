# -*- coding: utf-8 -*-
"""
用户管理 API（仅管理员）

- GET    /api/admin/users
- POST   /api/admin/users
- PATCH  /api/admin/users/{id}               {disabled: bool}
- POST   /api/admin/users/{id}/reset-password {password}
- GET    /api/admin/audit

作者：@zlxaaa
创建日期：2026-10-18
版本：1.0.0
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from core.auth import require_admin
from service import user_store, audit_store, note_store, history_store

router = APIRouter()


class CreateUserReq(BaseModel):
    username: str = Field(..., min_length=2, max_length=32)
    password: str = Field(..., min_length=8, max_length=128)
    role: str = Field("user")


class PatchUserReq(BaseModel):
    disabled: bool


class ResetPwdReq(BaseModel):
    password: str = Field(..., min_length=8, max_length=128)


@router.get("/users")
def list_users(_admin=Depends(require_admin)):
    return {"success": True, "data": {"items": user_store.list_users()}}


@router.post("/users")
def create_user(req: CreateUserReq, admin=Depends(require_admin)):
    if req.role not in ("admin", "user"):
        raise HTTPException(400, "role 必须是 admin 或 user")
    try:
        uid = user_store.create_user(req.username, req.password, role=req.role)
    except ValueError as e:
        raise HTTPException(409, str(e))
    audit_store.write(
        admin["id"], "add_user",
        target_user=uid,
        detail={"username": req.username, "role": req.role},
    )
    return {"success": True, "data": {"id": uid}}


@router.patch("/users/{user_id}")
def patch_user(user_id: int, req: PatchUserReq, admin=Depends(require_admin)):
    if user_id == admin["id"] and req.disabled:
        raise HTTPException(400, "不能禁用自己")
    try:
        user_store.set_disabled(user_id, req.disabled)
    except ValueError as e:
        raise HTTPException(404, str(e))
    action = "disable_user" if req.disabled else "enable_user"
    audit_store.write(admin["id"], action, target_user=user_id)
    return {"success": True}


@router.post("/users/{user_id}/reset-password")
def reset_pwd(user_id: int, req: ResetPwdReq, admin=Depends(require_admin)):
    try:
        user_store.reset_password(user_id, req.password)
    except ValueError as e:
        raise HTTPException(404, str(e))
    audit_store.write(admin["id"], "reset_password", target_user=user_id)
    return {"success": True}


@router.get("/audit")
def list_audit(page: int = 1, page_size: int = 20, _admin=Depends(require_admin)):
    if page < 1:
        page = 1
    if page_size < 1 or page_size > 100:
        page_size = 20
    return {"success": True, "data": audit_store.list_audit(page, page_size)}

@router.get("/hidden/notes")
def list_hidden_notes(page: int = 1, page_size: int = 20, _admin=Depends(require_admin)):
    if page < 1:
        page = 1
    if page_size < 1 or page_size > 100:
        page_size = 20
    return {"success": True, "data": note_store.list_hidden(page, page_size)}


@router.get("/hidden/history")
def list_hidden_history(page: int = 1, page_size: int = 20, _admin=Depends(require_admin)):
    if page < 1:
        page = 1
    if page_size < 1 or page_size > 100:
        page_size = 20
    return {"success": True, "data": history_store.list_hidden(page, page_size)}


@router.patch("/hidden/notes/{note_id}/unhide")
def unhide_note(note_id: int, admin=Depends(require_admin)):
    if not note_store.admin_unhide(note_id):
        raise HTTPException(404, "笔记不存在或不是隐藏状态")
    audit_store.write(admin["id"], "unhide_content",
                      target_type="note", target_id=note_id)
    return {"success": True}


@router.patch("/hidden/history/{history_id}/unhide")
def unhide_history(history_id: int, admin=Depends(require_admin)):
    if not history_store.admin_unhide(history_id):
        raise HTTPException(404, "历史不存在或不是隐藏状态")
    audit_store.write(admin["id"], "unhide_content",
                      target_type="history", target_id=history_id)
    return {"success": True}