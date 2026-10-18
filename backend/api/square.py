# -*- coding: utf-8 -*-
"""
广场 API：公开笔记 / 公开历史（需登录）+ 管理员隐藏

作者：@zlxaaa
创建日期：2026-10-18
版本：1.0.0
"""

from fastapi import APIRouter, Depends, HTTPException

from core.auth import require_user, require_admin
from service import note_store, history_store, audit_store

router = APIRouter()


@router.get("/notes")
def square_notes(page: int = 1, page_size: int = 20, q: str = "", user=Depends(require_user)):
    if page < 1: page = 1
    if page_size < 1 or page_size > 100: page_size = 20
    return {"success": True, "data": note_store.list_public(page, page_size, q)}


@router.get("/notes/{note_id}")
def square_note_detail(note_id: int, user=Depends(require_user)):
    item = note_store.get_public(note_id)
    if not item:
        raise HTTPException(404, "公开笔记不存在")
    return {"success": True, "data": item}


@router.get("/history")
def square_history(page: int = 1, page_size: int = 20, q: str = "", user=Depends(require_user)):
    if page < 1: page = 1
    if page_size < 1 or page_size > 100: page_size = 20
    return {"success": True, "data": history_store.list_public(page, page_size, q)}


@router.get("/history/{history_id}")
def square_history_detail(history_id: int, user=Depends(require_user)):
    item = history_store.get_public(history_id)
    if not item:
        raise HTTPException(404, "公开历史不存在")
    return {"success": True, "data": item}


@router.patch("/notes/{note_id}/hide")
def hide_note(note_id: int, admin=Depends(require_admin)):
    if not note_store.admin_hide(note_id):
        raise HTTPException(404, "笔记不存在")
    audit_store.write(admin["id"], "hide_content",
                      target_type="note", target_id=note_id)
    return {"success": True}


@router.patch("/history/{history_id}/hide")
def hide_history(history_id: int, admin=Depends(require_admin)):
    if not history_store.admin_hide(history_id):
        raise HTTPException(404, "历史记录不存在")
    audit_store.write(admin["id"], "hide_content",
                      target_type="history", target_id=history_id)
    return {"success": True}