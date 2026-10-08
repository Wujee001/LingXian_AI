# -*- coding: utf-8 -*-
"""
单减字识别接口模块

V1 核心：上传单个减字图片→classifier 识别 Top-3 候选→
parser 查知识库解析首选→返回候选置信度与演奏信息。
模型线 .pth 权重交付后仅替换 classifier，本接口不动。

作者：
    @Wujee

创建日期：2026-10-08
版本：1.0.0

许可证：内部使用，未经许可不得传播。

"""

import io

from fastapi import APIRouter, UploadFile, File
from PIL import Image

from service.classifier import predict_crop
from service.parser import char_parse
from utils.mlnlog import MLN_LOG_INFO, MLN_LOG_EXCEPTION

router = APIRouter()


@router.post("/predict")
async def single_predict(file: UploadFile = File(...)):
    """上传单个减字图片，返回 Top-3 候选与首选解析。"""
    try:
        contents = await file.read()
        img = Image.open(io.BytesIO(contents))

        candidates = predict_crop(img)
        top_key, top_conf = candidates[0]
        parse_result = char_parse(top_key)

        MLN_LOG_INFO(
            "单字识别：%s，首选=%s 置信度=%.2f",
            file.filename, top_key, top_conf,
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
            },
        }
    except Exception as e:
        MLN_LOG_EXCEPTION("单字识别异常：%s", e)
        return {"success": False, "data": {"msg": f"识别失败：{e}"}}