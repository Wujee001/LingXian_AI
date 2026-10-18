# -*- coding: utf-8 -*-
"""第一阶段：YOLO11 单类别减字区域检测。

与旧279类模型不同，class_id=0 仅表示“可见减字符号区域”，不能当作指法。
采用训练时一致的 768/600 重叠切片 + 960 输入尺寸；仅过滤内部切片截断框，
之后执行全图 NMS。任何异常不伪造候选，也不调用假模型。
"""
from __future__ import annotations

import os
from pathlib import Path

import cv2
import numpy as np

from core.config import MODEL_DIR
from utils.mlnlog import MLN_LOG_INFO, MLN_LOG_WARN, MLN_LOG_EXCEPTION

WEIGHT_PATH = Path(MODEL_DIR) / 'best.pt'
TILE = int(os.getenv('LINGXIAN_TILE', '768'))
STRIDE = int(os.getenv('LINGXIAN_STRIDE', '600'))
IMGSZ = int(os.getenv('LINGXIAN_IMGSZ', '960'))
CONF = float(os.getenv('LINGXIAN_CONF', '0.20'))
EDGE_PX = float(os.getenv('LINGXIAN_EDGE_PX', '2'))
IOU = float(os.getenv('LINGXIAN_NMS_IOU', '0.50'))
DEVICE = os.getenv('LINGXIAN_YOLO_DEVICE', 'cpu')

_model = None
_error = None


def _starts(length: int, tile: int, stride: int) -> list[int]:
    if length <= tile:
        return [0]
    return sorted(set(range(0, length - tile + 1, stride)) | {length - tile})


def _truncated(box, x0, y0, tw, th, w, h, edge: float) -> bool:
    l, t, r, b = map(float, box)
    return bool((x0 > 0 and l <= edge)
                or (x0 + tw < w and tw - r <= edge)
                or (y0 > 0 and t <= edge)
                or (y0 + th < h and th - b <= edge))


def _iou(a, b) -> float:
    x1, y1 = max(a[0], b[0]), max(a[1], b[1])
    x2, y2 = min(a[2], b[2]), min(a[3], b[3])
    inter = max(0, x2-x1) * max(0, y2-y1)
    aa = max(0, a[2]-a[0]) * max(0, a[3]-a[1])
    bb = max(0, b[2]-b[0]) * max(0, b[3]-b[1])
    return inter / (aa + bb - inter + 1e-9)


def _nms(boxes, confidences, iou: float = IOU) -> list[int]:
    pending = sorted(range(len(boxes)), key=lambda i: confidences[i], reverse=True)
    keep = []
    while pending:
        idx = pending.pop(0)
        keep.append(idx)
        pending = [j for j in pending if _iou(boxes[idx], boxes[j]) < iou]
    return keep


def _get_model():
    global _model, _error
    if _model is not None:
        return _model
    if not WEIGHT_PATH.is_file():
        _error = f'缺少第一阶段 YOLO 权重：{WEIGHT_PATH}'
        return None
    try:
        from ultralytics import YOLO
        model = YOLO(str(WEIGHT_PATH), task='detect')
        names = model.names
        if len(names) != 1 or str(list(names.values())[0]).lower() != 'jianzi':
            raise ValueError(f'需使用单类别 jianzi 检测权重，实际类别={names!r}。不要使用旧279类权重。')
        _model, _error = model, None
        MLN_LOG_INFO('Stage1 单类别 YOLO 加载成功: %s', WEIGHT_PATH)
    except Exception as exc:
        _error = f'第一阶段 YOLO 加载失败：{exc}'
        MLN_LOG_EXCEPTION('%s', _error)
    return _model


def status() -> dict:
    ready = _get_model() is not None
    return {'available': ready, 'model': 'YOLO11 jianzi 单类别区域检测',
            'weight': WEIGHT_PATH.name, 'error': None if ready else _error}


def available() -> bool:
    return _get_model() is not None


def detect_tiles(model, image: np.ndarray, tile: int = TILE, stride: int = STRIDE,
                 imgsz: int = IMGSZ, conf: float = CONF, edge_px: float = EDGE_PX,
                 device: str = DEVICE) -> tuple[list, list, int]:
    """依赖 model.predict 的可注入函数，便于不用真实权重也能做坐标单测。"""
    if not 0 < stride < tile:
        raise ValueError('切片参数必须满足 0 < stride < tile')
    h, w = image.shape[:2]
    boxes, confidences = [], []
    removed = 0
    for y0 in _starts(h, tile, stride):
        for x0 in _starts(w, tile, stride):
            chip = image[y0:y0+tile, x0:x0+tile]
            th, tw = chip.shape[:2]
            result = model.predict(source=chip, imgsz=imgsz, conf=conf, iou=IOU,
                                   device=device, verbose=False)[0]
            if result.boxes is None:
                continue
            for box, score in zip(result.boxes.xyxy.cpu().numpy(), result.boxes.conf.cpu().numpy()):
                if _truncated(box, x0, y0, tw, th, w, h, edge_px):
                    removed += 1
                    continue
                x1,y1,x2,y2 = map(float, box)
                b = [max(0, min(w, x1+x0)), max(0, min(h, y1+y0)),
                     max(0, min(w, x2+x0)), max(0, min(h, y2+y0))]
                if b[2] <= b[0] or b[3] <= b[1]:
                    continue
                boxes.append(b)
                confidences.append(float(score))
    kept = _nms(boxes, confidences)
    return [boxes[i] for i in kept], [confidences[i] for i in kept], removed


def _sort_items(items: list) -> list:
    """当前横向排版谱页按自上而下、同行自左至右排序；可设为 column 切竖排。"""
    if os.getenv('LINGXIAN_READING_ORDER', 'row').lower() == 'column':
        return sorted(items, key=lambda it: (-it['box']['x'], it['box']['y']))
    # 同行字形中心有细微高度差，按中位框高量化到邻近行。
    if not items: return []
    widths = [it['box']['h'] for it in items]
    tol = max(0.01, float(np.median(widths)) * 1.2)
    rows = []
    for it in sorted(items, key=lambda a: a['box']['y']+a['box']['h']/2):
        cy = it['box']['y']+it['box']['h']/2
        found = next((r for r in rows if abs(cy-r['center']) <= tol), None)
        if found is None:rows.append({'center':cy,'items':[it]})
        else:
            found['items'].append(it)
            found['center'] = sum(a['box']['y']+a['box']['h']/2 for a in found['items'])/len(found['items'])
    return [it for row in sorted(rows,key=lambda r:r['center'])
            for it in sorted(row['items'],key=lambda a:a['box']['x'])]


def recognize(image_path: str, conf: float = CONF):
    """兼容旧 API，返回 (success, items, (width,height))；成功即使零框也为 True。"""
    model = _get_model()
    if model is None:
        return False, [], None
    try:
        arr = np.fromfile(str(image_path), dtype=np.uint8)
        im = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if im is None: raise ValueError('谱图无法读取')
        h,w = im.shape[:2]
        boxes, scores, removed = detect_tiles(model, im, conf=conf)
        items = []
        for (x1,y1,x2,y2),score in zip(boxes,scores):
            items.append({'box': {'x':round(x1/w,6),'y':round(y1/h,6),
                                 'w':round((x2-x1)/w,6),'h':round((y2-y1)/h,6)},
                          'xyxy':[x1,y1,x2,y2],
                          'class_key':None,'raw_label':'jianzi',
                          'confidence':round(float(score),5)})
        items = _sort_items(items)
        MLN_LOG_INFO('Stage1 切片定位: 保留 %d 框，边缘过滤 %d 框',len(items),removed)
        return True, items, (w,h)
    except Exception as exc:
        MLN_LOG_EXCEPTION('Stage1 YOLO 检测异常: %s',exc)
        return False,[],None


def classify(*args,**kwargs):
    """不允许把单类别检测器冒充指法分类器。"""
    return False, []
