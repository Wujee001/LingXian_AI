# -*- coding: utf-8 -*-
"""
整谱打谱接口模块

V1 整谱闭环：上传整谱图→detector 规则画框→逐框裁剪→
classifier 识别 Top-3→parser 查知识库解析→低置信标 U 待复核。
人工修正通过 /correct 回流。

作者：
    @Wujee

创建日期：2026-10-1
版本：1.0.0

许可证：内部使用，未经许可不得传播。

"""

import os

from fastapi import APIRouter, UploadFile, File
from pydantic import BaseModel
from PIL import Image

from core.config import UPLOAD_DIR
from service.detector import detect
from service.classifier import predict_crop
from service.parser import char_parse
from utils.mlnlog import MLN_LOG_INFO, MLN_LOG_EXCEPTION

router = APIRouter()

# 低于该置信度的框标记为 U 人工复核
CONFIDENCE_TAU = 0.6


class SheetItem(BaseModel):
    index: int
    box: dict
    candidates: list
    parse_result: dict
    status: str


class SheetResp(BaseModel):
    success: bool
    data: dict


@router.post("/upload", response_model=SheetResp)
async def sheet_upload(file: UploadFile = File(...)):
    """上传整谱，返回检测框、逐框识别与解析结果。"""
    save_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(save_path, "wb") as f:
        f.write(await file.read())

    MLN_LOG_INFO("整谱上传：%s", file.filename)

    boxes = detect(save_path)

    sheet_img = Image.open(save_path)
    items = []

    for i, box in enumerate(boxes):
        try:
            candidates = _crop_and_predict(sheet_img, box)
            top_key, top_conf = candidates[0]
            parse_result = char_parse(top_key)

            status = "U" if top_conf < CONFIDENCE_TAU else "A"

            items.append({
                "index": i,
                "box": box,
                "candidates": candidates,
                "parse_result": parse_result,
                "status": status,
            })
        except Exception as e:
            MLN_LOG_EXCEPTION("第%d框处理异常：%s", i, e)

    return {
        "success": True,
        "data": {
            "image_url": f"/static/upload/{file.filename}",
            "items": items,
        },
    }


@router.post("/correct")
async def sheet_correct(payload: dict):
    """
    人工修正回流。

    入参：
        index：框序号
        box：调整后的框（可空）
        confirmed_key：人工确认的类别 key
    """
    MLN_LOG_INFO(
        "人工修正回流：index=%s key=%s",
        payload.get("index"),
        payload.get("confirmed_key"),
    )
    # TODO: 写入 SQLite 修正表，供模型线迭代训练
    return {"success": True, "data": {"msg": "修正已记录"}}


def _crop_and_predict(sheet_img: Image.Image, box: dict) -> list:
    """按归一化框裁剪，调用分类器，返回 [(key, conf), ...] Top-3。"""
    w, h = sheet_img.size
    crop = sheet_img.crop((
        int(box["x"] * w),
        int(box["y"] * h),
        int((box["x"] + box["w"]) * w),
        int((box["y"] + box["h"]) * h),
    ))
    return predict_crop(crop)
