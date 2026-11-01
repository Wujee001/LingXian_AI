# -*- coding: utf-8 -*-
"""整谱打谱接口"""
import os
import uuid
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel
from PIL import Image

from core.config import UPLOAD_DIR, LOG_DIR
from service.parser import char_parse
from service import correction_store
from utils.mlnlog import MLN_LOG_INFO, MLN_LOG_EXCEPTION, MLN_LOG_WARN

router = APIRouter()
CONFIDENCE_TAU = 0.6
ALLOWED_EXT = {".png", ".jpg", ".jpeg"}


class SheetResp(BaseModel):
    success: bool
    data: dict


@router.post("/upload", response_model=SheetResp)
async def sheet_upload(file: UploadFile = File(...)):
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXT:
        MLN_LOG_WARN("整谱上传被拒：%s", file.filename)
        raise HTTPException(status_code=400, detail="仅支持 PNG/JPG/JPEG")
    save_name = f"{uuid.uuid4().hex}{ext}"
    save_path = os.path.join(UPLOAD_DIR, save_name)
    content = await file.read()
    with open(save_path, "wb") as f:
        f.write(content)
    MLN_LOG_INFO("整谱上传：原名=%s 保存=%s", file.filename, save_name)

    try:
        sheet_img = Image.open(save_path)
        sheet_img.load()
    except Exception as e:
        MLN_LOG_EXCEPTION("整谱图无法解析：%s", e)
        raise HTTPException(status_code=400, detail="图片损坏")

    items, source = _recognize(save_path, sheet_img)
    return {
        "success": True,
        "data": {
            "image_url": f"/static/upload/{save_name}",
            "source": source,
            "items": items,
        },
    }


def _build_item(index: int, box: dict, candidates: list, raw_label):
    if candidates:
        top_key, top_conf = candidates[0]
        return {
            "index": index,
            "box": box,
            "candidates": [[k, c] for k, c in candidates],
            "parse_result": char_parse(top_key),
            "status": "U" if top_conf < CONFIDENCE_TAU else "A",
            "raw_label": raw_label,
        }
    return {
        "index": index,
        "box": box,
        "candidates": [],
        "parse_result": None,
        "status": "U",
        "raw_label": raw_label,
    }


def _recognize(save_path: str, sheet_img: Image.Image):
    # Stage1：YOLO出框
    from service import yolo_infer
    yolo_items = []
    try:
        ok, yitems, _ = yolo_infer.recognize(save_path)
        if ok and yitems:
            yolo_items = yitems
    except Exception as e:
        MLN_LOG_EXCEPTION("Stage1 YOLO 异常：%s", e)
        raise HTTPException(status_code=500, detail="检测模型异常，请联系开发人员检查")

    if not yolo_items:
        MLN_LOG_WARN("Stage1未检测到减字")
        return [], "local"

    # Stage2：本地识别
    from service.stage2_infer import predict_crop, available as stage2_available
    if not stage2_available():
        raise HTTPException(status_code=503, detail="识别模型未就绪，请联系开发人员检查")

    items = []
    for i, d in enumerate(yolo_items):
        box = d["box"]
        crop = sheet_img.crop((
            int(box["x"] * sheet_img.width),
            int(box["y"] * sheet_img.height),
            int((box["x"] + box["w"]) * sheet_img.width),
            int((box["y"] + box["h"]) * sheet_img.height),
        ))
        ok, cands = predict_crop(crop)
        if not ok:
            cands = []
        items.append(_build_item(i, box, cands, d.get("raw_label")))
    MLN_LOG_INFO("整谱本地识别完成，共%d框", len(items))
    return items, "local"


@router.post("/correct")
async def sheet_correct(payload: dict):
    """人工修正，追加写入 utils/logs/feedback.txt，并落库 corrections.json"""
    total = correction_store.append(payload)
    feedback_line = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 图={payload.get('image_url')} 框#{payload.get('index')} 原识别={payload.get('origin_key')} → 人工修正={payload.get('confirmed_key')}\n"
    # 统一写入 backend/utils/logs/feedback.txt
    os.makedirs(LOG_DIR, exist_ok=True)
    feedback_path = os.path.join(LOG_DIR, "feedback.txt")
    with open(feedback_path, "a", encoding="utf-8") as f:
        f.write(feedback_line)
    MLN_LOG_INFO("人工修正已记录：%s", feedback_line.strip())
    return {"success": True, "data": {"msg": "修正已记录，感谢反馈", "total": total}}
