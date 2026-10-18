# -*- coding: utf-8 -*-
"""
个人笔记 API（需登录）

作者：@zlxaaa
创建日期：2026-10-18
版本：1.0.0
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from core.auth import require_user
from service import note_store

router = APIRouter()


class NoteCreate(BaseModel):
    title: str | None = None
    content_md: str = Field(..., min_length=1, max_length=20000)
    class_key: str | None = None
    visibility: str = "private"


class NoteUpdate(NoteCreate):
    pass


class VisibilityReq(BaseModel):
    visibility: str = Field(..., pattern="^(private|public)$")


def _check_vis(v: str) -> None:
    if v not in ("private", "public"):
        raise HTTPException(400, "visibility 必须是 private / public")


@router.get("")
def list_notes(page: int = 1, page_size: int = 20, q: str = "", user=Depends(require_user)):
    if page < 1: page = 1
    if page_size < 1 or page_size > 100: page_size = 20
    return {"success": True, "data": note_store.list_mine(user["id"], page, page_size, q)}


@router.post("")
def create_note(req: NoteCreate, user=Depends(require_user)):
    _check_vis(req.visibility)
    nid = note_store.create(user["id"], req.title, req.content_md, req.class_key, req.visibility)
    return {"success": True, "data": {"id": nid}}


@router.get("/{note_id}")
def get_note(note_id: int, user=Depends(require_user)):
    item = note_store.get_one(note_id, user["id"])
    if not item:
        raise HTTPException(404, "笔记不存在")
    return {"success": True, "data": item}


@router.put("/{note_id}")
def update_note(note_id: int, req: NoteUpdate, user=Depends(require_user)):
    _check_vis(req.visibility)
    ok = note_store.update(note_id, user["id"], req.title, req.content_md,
                           req.class_key, req.visibility)
    if not ok:
        raise HTTPException(404, "笔记不存在")
    return {"success": True}


@router.delete("/{note_id}")
def delete_note(note_id: int, user=Depends(require_user)):
    if not note_store.delete(note_id, user["id"]):
        raise HTTPException(404, "笔记不存在")
    return {"success": True}


@router.patch("/{note_id}/visibility")
def set_visibility(note_id: int, req: VisibilityReq, user=Depends(require_user)):
    try:
        ok = note_store.set_visibility(note_id, user["id"], req.visibility)
    except PermissionError as e:
        raise HTTPException(403, str(e))
    if not ok:
        raise HTTPException(404, "笔记不存在")
    return {"success": True}