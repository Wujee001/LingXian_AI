# -*- coding: utf-8 -*-
"""单个减字：Stage-2 八字段属性 Top-3（实际输出）与保守释义。"""
import io
import os

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from PIL import Image, UnidentifiedImageError

from service.attribute_parser import get_top1, parse_attributes
from service.parser import char_parse

router = APIRouter()
ALLOWED={'.jpg','.jpeg','.png'}
MAX_UPLOAD=20*1024*1024


class AttrReq(BaseModel):
    attributes: dict[str,str]


@router.get('/model-status')
def model_status():
    from service.stage2_reader import status
    return {'success':True,'data':status()}


@router.post('/parse-attributes')
def parse_selected(req:AttrReq):
    """仅格式化人工选择的显式字段；不推导省写和节奏。"""
    return {'success':True,'data':parse_attributes(req.attributes)}


@router.post('/predict')
async def single_predict(file:UploadFile=File(...),engine:str=Form('auto')):
    ext=os.path.splitext(file.filename or '')[1].lower()
    if ext not in ALLOWED:
        raise HTTPException(status_code=400,detail='仅支持 PNG/JPG/JPEG')
    content=await file.read()
    if len(content)>MAX_UPLOAD:
        raise HTTPException(status_code=413,detail='图片超过20MB')
    try:
        image=Image.open(io.BytesIO(content)).convert('RGB')
        image.load()
    except (UnidentifiedImageError,OSError,ValueError):
        raise HTTPException(status_code=400,detail='图片无法读取')

    engine=(engine or 'auto').lower()
    if engine not in ('auto','yolo','qwen'):
        raise HTTPException(status_code=400,detail='不支持的识别引擎')

    if engine=='qwen':
        from service.qwen_adapter import classify_crop
        ok,candidates=classify_crop(image)
        if not ok or not candidates:
            raise HTTPException(status_code=503,detail='多模态识别不可用：检查 API Key、网络或额度')
        key,conf=candidates[0]
        return {'success':True,'data':{
            'candidates':[{'class_key':key,'confidence':score} for key,score in candidates],
            'top_key':key,'top_confidence':conf,'parse_result':char_parse(key),
            'source':'qwen','status':'U','needs_review':True,
            'review_reasons':['多模态候选未经过专家核对'],
            'attributes_top3':{},'attributes_selected':{},
        }}

    from service.stage2_reader import get_reader, status
    reader=get_reader()
    if reader is None:
        raise HTTPException(status_code=503,detail=status().get('error') or '第二阶段识别模型尚未安装')
    pred=reader.predict_boxes(image,[(0,0,image.width,image.height)])[0]
    attrs=get_top1(pred)
    return {'success':True,'data':{
        'candidates':[], 'top_key':None,'top_confidence':None,
        'attributes_top3':pred['attributes_top3'],
        'attributes_selected':attrs,
        'parse_result':parse_attributes(attrs),
        'source':'stage2','status':'U','needs_review':True,
        'review_reasons':pred['review_reasons'],
    }}
