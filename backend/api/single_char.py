# -*- coding: utf-8 -*-
"""单减字识别接口（纯本地两阶段，无云API）"""
import io
import os
from fastapi import APIRouter, File, HTTPException, UploadFile
from PIL import Image, UnidentifiedImageError

from service.parser import char_parse
from service.stage2_infer import predict_crop, available as stage2_available
from utils.mlnlog import MLN_LOG_INFO, MLN_LOG_WARN

router = APIRouter()
ALLOWED = {'.jpg', '.jpeg', '.png'}
MAX_UPLOAD = 20 * 1024 * 1024


@router.post('/predict')
async def single_predict(file: UploadFile = File(...)):
    ext = os.path.splitext(file.filename or '')[1].lower()
    if ext not in ALLOWED:
        MLN_LOG_WARN("单字上传格式不支持：%s", file.filename)
        raise HTTPException(status_code=400, detail='仅支持 PNG/JPG/JPEG')
    content = await file.read()
    if len(content) > MAX_UPLOAD:
        raise HTTPException(status_code=413, detail='图片超过20MB')
    try:
        image = Image.open(io.BytesIO(content)).convert('RGB')
        image.load()
    except (UnidentifiedImageError, OSError, ValueError):
        raise HTTPException(status_code=400, detail='图片无法读取')

    if not stage2_available():
        MLN_LOG_WARN("本地识别模型未加载，拒绝请求")
        raise HTTPException(status_code=503, detail='本地模型未就绪，请联系开发人员检查')

    ok, candidates = predict_crop(image)
    if not ok or not candidates:
        raise HTTPException(status_code=500, detail='识别失败，请联系开发人员检查')

    key, conf = candidates[0]
    MLN_LOG_INFO("单字本地识别完成：%s 置信度=%.3f", key, conf)
    return {
        'success': True,
        'data': {
            'candidates': candidates,
            'top_key': key,
            'top_confidence': conf,
            'parse_result': char_parse(key),
            'source': 'local',
            'status': 'U',
        }
    }
