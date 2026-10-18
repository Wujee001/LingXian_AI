# -*- coding: utf-8 -*-
"""
历史记录 API（需登录）

- GET    /api/history
- GET    /api/history/{id}
- DELETE /api/history/{id}
- PATCH  /api/history/{id}/visibility

作者：@zlxaaa
创建日期：2026-10-18
版本：1.0.0
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from core.auth import require_user
from service import history_store

router = APIRouter()


class VisibilityReq(BaseModel):
    visibility: str = Field(..., pattern="^(private|public)$")


@router.get("")
def list_history(page: int = 1, page_size: int = 20, q: str = "", user=Depends(require_user)):
    if page < 1:
        page = 1
    if page_size < 1 or page_size > 100:
        page_size = 20
    return {"success": True, "data": history_store.list_mine(user["id"], page, page_size, q)}


@router.get("/{history_id}")
def get_history(history_id: int, user=Depends(require_user)):
    item = history_store.get_one(history_id, user["id"])
    if not item:
        raise HTTPException(404, "历史记录不存在")
    return {"success": True, "data": item}


@router.delete("/{history_id}")
def delete_history(history_id: int, user=Depends(require_user)):
    if not history_store.delete(history_id, user["id"]):
        raise HTTPException(404, "历史记录不存在")
    return {"success": True}


@router.patch("/{history_id}/visibility")
def set_visibility(history_id: int, req: VisibilityReq, user=Depends(require_user)):
    try:
        ok = history_store.set_visibility(history_id, user["id"], req.visibility)
    except PermissionError as e:
        raise HTTPException(403, str(e))
    if not ok:
        raise HTTPException(404, "历史记录不存在")
    return {"success": True}