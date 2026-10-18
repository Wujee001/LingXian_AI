# -*- coding: utf-8 -*-
"""单个减字：Stage-2 八字段属性 Top-3（实际输出）与保守释义。

阶段 2：登录用户识别成功后写入历史快照；未登录不写。

作者：@Wujee
维护：@zlxaaa
"""
import io
import os

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from PIL import Image, UnidentifiedImageError

from core.auth import optional_user
from service.attribute_parser import get_top1, parse_attributes
from service.parser import char_parse
from utils.mlnlog import MLN_LOG_EXCEPTION

router = APIRouter()
ALLOWED = {'.jpg', '.jpeg', '.png'}
MAX_UPLOAD = 20 * 1024 * 1024


class AttrReq(BaseModel):
    attributes: dict[str, str]


def _write_history(user_id, query_key, payload, pil_image):
    try:
        from service import history_store
        history_store.write_single(user_id, query_key, payload, pil_image)
    except Exception as e:
        MLN_LOG_EXCEPTION("单字历史写入异常：%s", e)


@router.get('/model-status')
def model_status():
    from service.stage2_reader import status
    return {'success': True, 'data': status()}


@router.post('/parse-attributes')
def parse_selected(req: AttrReq):
    return {'success': True, 'data': parse_attributes(req.attributes)}


@router.post('/predict')
async def single_predict(
    file: UploadFile = File(...),
    engine: str = Form('auto'),
    user=Depends(optional_user),
):
    ext = os.path.splitext(file.filename or '')[1].lower()
    if ext not in ALLOWED:
        raise HTTPException(status_code=400, detail='仅支持 PNG/JPG/JPEG')
    content = await file.read()
    if len(content) > MAX_UPLOAD:
        raise HTTPException(status_code=413, detail='图片超过20MB')
    try:
        image = Image.open(io.BytesIO(content)).convert('RGB')
        image.load()
    except (UnidentifiedImageError, OSError, ValueError):
        raise HTTPException(status_code=400, detail='图片无法读取')

    engine = (engine or 'auto').lower()
    if engine not in ('auto', 'yolo', 'qwen'):
        raise HTTPException(status_code=400, detail='不支持的识别引擎')

    if engine == 'qwen':
        from service.qwen_adapter import classify_crop
        ok, candidates = classify_crop(image)
        if not ok or not candidates:
            raise HTTPException(status_code=503, detail='多模态识别不可用：检查 API Key、网络或额度')
        key, conf = candidates[0]
        resp_data = {
            'candidates': [{'class_key': k, 'confidence': s} for k, s in candidates],
            'top_key': key,
            'top_confidence': conf,
            'parse_result': char_parse(key),
            'source': 'qwen',
            'status': 'U',
            'needs_review': True,
            'review_reasons': ['多模态候选未经过专家核对'],
            'attributes_top3': {},
            'attributes_selected': {},
        }
        if user:
            _write_history(user['id'], key, resp_data, image)
        return {'success': True, 'data': resp_data}

    from service.stage2_reader import get_reader, status
    reader = get_reader()
    if reader is None:
        raise HTTPException(status_code=503, detail=status().get('error') or '第二阶段识别模型尚未安装')
    pred = reader.predict_boxes(image, [(0, 0, image.width, image.height)])[0]
    attrs = get_top1(pred)
    resp_data = {
        'candidates': [],
        'top_key': None,
        'top_confidence': None,
        'attributes_top3': pred['attributes_top3'],
        'attributes_selected': attrs,
        'parse_result': parse_attributes(attrs),
        'source': 'stage2',
        'status': 'U',
        'needs_review': True,
        'review_reasons': pred['review_reasons'],
    }
    if user:
        _write_history(user['id'], None, resp_data, image)
    return {'success': True, 'data': resp_data}