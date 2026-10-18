# -*- coding: utf-8 -*-
"""
历史快照图片存储

- 从 PIL Image 或已落盘文件复制到 data/history_images/{user_id}/{uuid}.{ext}
- 同步生成缩略图 {uuid}_thumb.jpg（长边 ≤ 400px）
- 返回相对路径（不含 HISTORY_IMG_DIR 前缀），供 DB 存储
- 删除时同时清理原图和缩略图

作者：@zlxaaa
创建日期：2026-10-18
版本：1.0.0
"""

import os
import shutil
import uuid

from PIL import Image

from core.config import HISTORY_IMG_DIR
from utils.mlnlog import MLN_LOG_EXCEPTION

THUMB_MAX = 400
THUMB_QUALITY = 82
ALLOWED_EXT = {".png", ".jpg", ".jpeg"}


def _ensure_dir(user_id: int) -> str:
    d = os.path.join(HISTORY_IMG_DIR, str(user_id))
    os.makedirs(d, exist_ok=True)
    return d


def _make_thumb(pil_image: Image.Image, out_path: str) -> None:
    thumb = pil_image.copy()
    thumb.thumbnail((THUMB_MAX, THUMB_MAX))
    if thumb.mode not in ("RGB", "L"):
        thumb = thumb.convert("RGB")
    thumb.save(out_path, format="JPEG", quality=THUMB_QUALITY)


def save_from_pil(pil_image: Image.Image, user_id: int):
    """从 PIL Image 保存；返回 (相对图片路径, 相对缩略图路径)，失败返回 None。"""
    try:
        d = _ensure_dir(user_id)
        name = uuid.uuid4().hex
        abs_img = os.path.join(d, f"{name}.png")
        abs_thumb = os.path.join(d, f"{name}_thumb.jpg")
        img = pil_image if pil_image.mode in ("RGB", "L") else pil_image.convert("RGB")
        img.save(abs_img, format="PNG")
        _make_thumb(img, abs_thumb)
        return f"{user_id}/{name}.png", f"{user_id}/{name}_thumb.jpg"
    except Exception as e:
        MLN_LOG_EXCEPTION("保存历史图片失败（PIL）：%s", e)
        return None


def save_from_file(source_path: str, user_id: int, ext: str = ".png"):
    """从已有文件复制；ext 保留原格式（.png/.jpg/.jpeg）。"""
    try:
        ext = (ext or ".png").lower()
        if ext not in ALLOWED_EXT:
            ext = ".png"
        d = _ensure_dir(user_id)
        name = uuid.uuid4().hex
        abs_img = os.path.join(d, f"{name}{ext}")
        abs_thumb = os.path.join(d, f"{name}_thumb.jpg")
        shutil.copyfile(source_path, abs_img)
        with Image.open(abs_img) as im:
            _make_thumb(im, abs_thumb)
        return f"{user_id}/{name}{ext}", f"{user_id}/{name}_thumb.jpg"
    except Exception as e:
        MLN_LOG_EXCEPTION("保存历史图片失败（文件）：%s", e)
        return None


def delete(rel_img: str | None, rel_thumb: str | None) -> None:
    """删除时忽略错误；目标不存在视为成功。"""
    for rel in (rel_img, rel_thumb):
        if not rel:
            continue
        try:
            abs_path = os.path.join(HISTORY_IMG_DIR, rel)
            if os.path.isfile(abs_path):
                os.remove(abs_path)
        except Exception as e:
            MLN_LOG_EXCEPTION("删除历史图片失败：%s -> %s", rel, e)