# -*- coding: utf-8 -*-
"""整谱 API：Stage1 单类定位 → Stage2 八字段候选，明确人工复核。

与旧接口兼容：data.image_url、data.items[*].box/status/parse_result/candidates；
新增 attributes_top3、attributes_selected、detection_confidence、review_reasons。
不再把 YOLO 类别 0 当古琴指法，也不隐式回退演示数据。
"""
from __future__ import annotations
import io
import os
import uuid

from fastapi import APIRouter,File,Form,HTTPException,UploadFile
from PIL import Image,UnidentifiedImageError

from core.config import UPLOAD_DIR
from service.attribute_parser import get_top1,parse_attributes
from service.parser import char_parse
from service import correction_store

router=APIRouter()
ALLOWED={'.jpg','.jpeg','.png'}
MAX_UPLOAD=20*1024*1024


@router.get('/model-status')
def model_status():
    from service import yolo_infer, stage2_reader
    return {'success':True,'data':{'stage1':yolo_infer.status(),
                                   'stage2':stage2_reader.status(),
                                   'flow':'YOLO jianzi 区域检测 → ResNet18 显式属性候选 → 用户确认'}}


def _new_item(index, det, attr_pred=None, qwen_candidates=None):
    box=det['box']
    base={'index':index,'box':box,'detection_confidence':det['confidence'],
          'raw_label':'jianzi','status':'U','candidates':[],
          'attributes_top3':{},'attributes_selected':{},
          'parse_result':None,'review_reasons':[]}
    if attr_pred is not None:
        attr=get_top1(attr_pred)
        base.update(attributes_top3=attr_pred['attributes_top3'],
                    attributes_selected=attr,
                    parse_result=parse_attributes(attr),
                    review_reasons=list(attr_pred.get('review_reasons',[])))
    elif qwen_candidates:
        key,score=qwen_candidates[0]
        base.update(candidates=[[k,float(p)] for k,p in qwen_candidates],
                    parse_result=char_parse(key),
                    review_reasons=['Qwen 多模态候选：须人工核对'])
    else:
        base['review_reasons']=['第二阶段尚未可用：请人工识别该框']
    return base


@router.post('/upload')
async def sheet_upload(file:UploadFile=File(...),engine:str=Form('auto')):
    ext=os.path.splitext(file.filename or '')[1].lower()
    if ext not in ALLOWED:
        raise HTTPException(status_code=400,detail='仅支持 PNG/JPG/JPEG')
    engine=(engine or 'auto').lower()
    if engine not in ('auto','yolo','qwen'):
        raise HTTPException(status_code=400,detail='未知识别引擎')
    contents=await file.read()
    if len(contents)>MAX_UPLOAD:
        raise HTTPException(status_code=413,detail='图片超过20MB')
    try:
        image=Image.open(io.BytesIO(contents)).convert('RGB')
        image.load()
    except (OSError,ValueError,UnidentifiedImageError):
        raise HTTPException(status_code=400,detail='无法解析图片')
    save_name=uuid.uuid4().hex+ext
    save_path=os.path.join(UPLOAD_DIR,save_name)
    with open(save_path,'wb') as f:f.write(contents)

    from service import yolo_infer
    ok,detected,_=yolo_infer.recognize(save_path)
    if not ok:
        from service import stage2_reader
        return {'success':True,'data':{
            'image_url':f'/static/upload/{save_name}','engine':engine,'source':'unavailable',
            'items':[],
            'warning':'第一阶段 YOLO 定位不可用。请检查模型文件或手动画框；不会用演示框冒充模型结果。',
            'model_status':{'stage1':yolo_infer.status(),'stage2':stage2_reader.status()}
        }}

    items=[]
    if engine=='qwen':
        from service.qwen_adapter import classify_crop
        for i,det in enumerate(detected):
            box=det['box']; w,h=image.size
            crop=image.crop((int(box['x']*w),int(box['y']*h),
                             int((box['x']+box['w'])*w),int((box['y']+box['h'])*h)))
            ok2,cands=classify_crop(crop)
            items.append(_new_item(i,det,qwen_candidates=cands if ok2 else None))
        source='stage1_yolo+qwen'
    else:
        from service import stage2_reader
        reader=stage2_reader.get_reader()
        stage2_rows=[]
        if reader is not None and detected:
            # 模型的裁剪严格使用 original-size xyxy，不能使用浏览器 CSS 尺寸。
            stage2_rows=reader.predict_boxes(image,[det['xyxy'] for det in detected])
        for i,det in enumerate(detected):
            attr=stage2_rows[i] if i<len(stage2_rows) else None
            items.append(_new_item(i,det,attr_pred=attr))
        source='stage1_yolo+stage2' if reader else 'stage1_yolo_only'

    return {'success':True,'data':{'image_url':f'/static/upload/{save_name}',
                                  'engine':engine,'source':source,'items':items,
                                  'warning':None if items else '未找到减字区域，可手动画框',
                                  'model_limits':'单类别检测只负责定位；指法属性为候选而非专家确认；不自动恢复省写或节奏'}}


@router.post('/correct')
async def sheet_correct(payload:dict):
    """记录用户人工确认的框和属性（人工确认之前一律 U）。"""
    total=correction_store.append(payload)
    if total<0:
        raise HTTPException(status_code=500,detail='人工修正保存失败')
    return {'success':True,'data':{'msg':'人工修正已记录','total':total}}
