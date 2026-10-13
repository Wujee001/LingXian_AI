# -*- coding: utf-8 -*-
"""
单减字识别接口模块（泠弦智谱 V1）

上传单个减字图片 → classifier 三级降级识别（YOLO→多模态→假数据）
→ parser 查知识库解析首选 → 返回候选置信度与演奏信息。
支持 PNG / JPG / JPEG。

作者：
    @Wujee

更新日期：2026-10-13
版本：2.0.0

许可证：内部使用，未经许可不得传播。

"""

import io
import os

from fastapi import APIRouter, UploadFile, File, Form
from PIL import Image

from service.classifier import predict_crop, get_last_source
from service.parser import char_parse
from utils.mlnlog import MLN_LOG_INFO, MLN_LOG_EXCEPTION, MLN_LOG_WARN

router = APIRouter()

ALLOWED_EXT = {".png", ".jpg", ".jpeg"}


@router.post("/predict")
async def single_predict(file: UploadFile = File(...),
                         engine: str = Form("auto")):
    """上传单个减字图片，返回 Top-3 候选、首选解析与来源路线。

    engine：auto 自动 / yolo 本地模型 / qwen 多模态（前端手动切换）。
    """
    try:
        ext = os.path.splitext(file.filename or "")[1].lower()
        if ext not in ALLOWED_EXT:
            MLN_LOG_WARN("单字上传被拒（非 PNG/JPG 图片）：%s", file.filename)
            return {"success": False,
                    "data": {"msg": "仅支持 PNG / JPG / JPEG 格式图片"}}

        contents = await file.read()
        img = Image.open(io.BytesIO(contents))
        img.load()

        candidates = predict_crop(img, engine)
        source = get_last_source()
        top_key, top_conf = candidates[0]
        parse_result = char_parse(top_key)

        MLN_LOG_INFO(
            "单字识别（引擎=%s 实际=%s）：%s，首选=%s 置信度=%.2f",
            engine, source, file.filename, top_key, top_conf,
        )

        return {
            "success": True,
            "data": {
                "candidates": [
                    {"class_key": key, "confidence": conf}
                    for key, conf in candidates
                ],
                "top_key": top_key,
                "top_confidence": top_conf,
                "parse_result": parse_result,
                "source": source,
            },
        }
    except Exception as e:
        MLN_LOG_EXCEPTION("单字识别异常：%s", e)
        return {"success": False, "data": {"msg": f"识别失败：{e}"}}
