# -*- coding: utf-8 -*-
"""
统一 YOLO 推理服务（泠弦智谱 V1 主识别路线）

模型线交付的是检测+分类一体的 Ultralytics YOLO 权重
（backend/models/best.pt），一次推理同时输出检测框、类别与置信度，
天然覆盖「整谱打谱」与「单减字识别」两条链路。

本模块职责：
    1. 懒加载单例 YOLO 权重（CPU 推理，只加载一次）；
    2. 把模型自带的 names（id->名称，可能是中文 display_name
       或拼音 class_key）动态对齐到 class_registry.csv 的 class_key；
    3. 对外提供统一结果：
         recognize(img)   整谱：排序后的 [{box, class_key, confidence}]
         classify(pil)    单字：Top-3 [(class_key, confidence), ...]
    4. 未安装 ultralytics / 无权重 / 权重损坏 / 推理异常时，
       available() 返回 False，由上层走「阿里云多模态 -> 假数据」降级，
       本模块不抛异常打断业务。

注意：图片一律转成 numpy 数组再送入模型，规避 ultralytics/cv2
对中文路径 imread 失败的问题。

作者：
    @Wujee

创建日期：2026-10-13
版本：1.0.0

许可证：内部使用，未经许可不得传播。

"""

import os

import numpy as np

from core.config import MODEL_DIR
from utils.mlnlog import MLN_LOG_INFO, MLN_LOG_WARN, MLN_LOG_EXCEPTION, MLN_LOG_DEBUG

# 模型线交付的 YOLO 权重（.gitignore 已忽略 *.pt，走 GitHub Release）
_WEIGHT_PATH = os.path.join(MODEL_DIR, "best.pt")

# 推理参数
_CONF_THRES = 0.25      # 置信度阈值
_IMGSZ = 960            # 整谱推理输入尺寸（大谱图文字小，适当放大）

# 运行期单例
_model = None
_checked = False
_ready = False
_name_to_key = None
_valid_keys = set()      # 注册表内全部合法 class_key（用于过滤模型细类标签）


# ==============================================================================
# 可用性与懒加载
# ==============================================================================
def available() -> bool:
    """
    YOLO 权重是否就绪。首次调用时懒加载，全程只检测一次。
    """
    global _checked
    if not _checked:
        _ensure_model()
    return _ready


def _ensure_model() -> bool:
    """加载权重并构建名称映射；任一环节失败都安全降级。"""
    global _model, _checked, _ready, _name_to_key, _valid_keys
    if _checked:
        return _ready
    _checked = True

    if not os.path.exists(_WEIGHT_PATH):
        MLN_LOG_WARN("未发现 YOLO 权重 %s，识别将走多模态/假数据兜底", _WEIGHT_PATH)
        _ready = False
        return False

    try:
        from ultralytics import YOLO

        net = YOLO(_WEIGHT_PATH, task="detect")
        names = getattr(net, "names", None) or {}
        _name_to_key, _valid_keys = _build_name_map(names)

        _model = net
        _ready = True
        MLN_LOG_INFO("YOLO 权重加载成功：%s（模型 %d 类，成功映射 %d 类）",
                     _WEIGHT_PATH, len(names),
                     sum(1 for v in _name_to_key.values() if v))
        return True
    except Exception as e:
        MLN_LOG_EXCEPTION("YOLO 权重加载失败，降级多模态/假数据：%s", e)
        _model, _ready = None, False
        return False


def _build_name_map(names: dict):
    """
    构建模型原始名称 -> class_key 的映射。

    模型实际输出是 279 个「细粒度中文演奏标签」（如
    「撮 3、6弦 · 大指九徽按3弦」），而注册表 class_registry.csv
    只维护 25 个基础 class_key，绝大多数细类无法一一对应：
        精确 class_key > 精确 display_name > 归一化模糊匹配；
        映射不上的名称对应值置 None（不再把中文长标签当 key），
        该框改由上层调用多模态重新认字，避免把长中文串当 key。

    返回：(原始名->class_key 或 None 的映射, 合法 class_key 集合)
    """
    try:
        from service.registry import all_classes
        rows = all_classes(only_active=True)
    except Exception as e:
        MLN_LOG_EXCEPTION("读取注册表失败，YOLO 名称映射降级为原值：%s", e)
        rows = []

    key_set = {r["class_key"] for r in rows}
    disp_map = {}
    norm_map = {}
    for r in rows:
        ck = r["class_key"]
        dn = (r.get("display_name") or "").strip()
        if dn:
            disp_map[dn] = ck
            norm_map[_norm(dn)] = ck
        norm_map[_norm(ck)] = ck

    result = {}
    matched = 0
    for _, raw in names.items():
        name = str(raw).strip()
        if name in key_set:
            result[name] = name
        elif name in disp_map:
            result[name] = disp_map[name]
        elif _norm(name) in norm_map:
            result[name] = norm_map[_norm(name)]
        else:
            result[name] = None      # 细类标签，注册表无对应基础 key
            matched += 0
            continue
        matched += 1
    MLN_LOG_INFO("YOLO 名称映射：%d 个模型标签中 %d 个可直接对应注册表基础 key",
                 len(names), matched)
    return result, key_set


def _norm(text: str) -> str:
    """归一化名称：小写、去空格/下划线/常见连接符，便于中英模糊对齐。"""
    return "".join(ch for ch in str(text).lower()
                   if ch not in " _-－—·.,，。:：()（）")


def _resolve_key(name: str):
    """模型名称 -> 合法 class_key；细类标签无法对应时返回 None（交由多模态认字）。"""
    if _name_to_key is None:
        return None
    return _name_to_key.get(str(name).strip())


# ==============================================================================
# 图像读取（兼容中文路径）
# ==============================================================================
def _read_bgr(path: str):
    """用 imdecode 读图，规避 cv2.imread 对中文路径返回 None。"""
    import cv2
    data = np.fromfile(path, dtype=np.uint8)
    img = cv2.imdecode(data, cv2.IMREAD_COLOR)
    return img


# ==============================================================================
# 统一结果结构
# ==============================================================================
def _raw_predict(img, conf: float, imgsz: int):
    """
    对 numpy 数组（BGR）跑一次 YOLO。

    返回：
        [(x1, y1, x2, y2, score, class_key, raw_name), ...]  像素坐标，未排序
        class_key 可能为 None（模型细类标签无法对应注册表基础 key）；
        raw_name 为模型原始中文标签，供前端展示「模型初判」。
    """
    results = _model.predict(img, conf=conf, imgsz=imgsz, verbose=False)
    if not results:
        return []
    boxes = getattr(results[0], "boxes", None)
    if boxes is None or len(boxes) == 0:
        return []

    xyxy = boxes.xyxy.cpu().numpy()
    confs = boxes.conf.cpu().numpy()
    clss = boxes.cls.cpu().numpy().astype(int)
    names = getattr(_model, "names", {})

    out = []
    for (x1, y1, x2, y2), score, cid in zip(xyxy, confs, clss):
        raw_name = str(names.get(int(cid), str(cid)))
        out.append((float(x1), float(y1), float(x2), float(y2),
                    round(float(score), 4), _resolve_key(raw_name), raw_name))
    return out


def recognize(image_path: str, conf: float = _CONF_THRES):
    """
    整谱识别（打谱主链路）。

    返回：
        成功 -> (True, [{"box": {x,y,w,h} 归一化,
                         "class_key": str|None, "confidence": float,
                         "raw_label": str}, ...], (W,H))
        失败 -> (False, [], None)
        class_key 为 None 表示模型细类标签无法对应注册表，需多模态认字；
        raw_label 为模型原始中文标签。框已按古琴竖排排序。
    """
    if not available():
        return False, [], None
    try:
        img = _read_bgr(image_path)
        if img is None:
            MLN_LOG_WARN("YOLO 读图失败（可能损坏/格式不支持）：%s", image_path)
            return False, [], None
        h, w = img.shape[:2]

        raw = _raw_predict(img, conf, _IMGSZ)
        items = []
        for x1, y1, x2, y2, score, key, raw_name in raw:
            items.append({
                "box": {
                    "x": round(max(x1, 0) / w, 4),
                    "y": round(max(y1, 0) / h, 4),
                    "w": round(min((x2 - x1) / w, 1.0), 4),
                    "h": round(min((y2 - y1) / h, 1.0), 4),
                },
                "class_key": key,
                "confidence": score,
                "raw_label": raw_name,
            })
        items = _sort_guqin(items)
        MLN_LOG_INFO("Stage1 YOLO 框检测完成：%d 个减字框，送入Stage2解析", len(items))
        return True, items, (w, h)
    except Exception as e:
        MLN_LOG_EXCEPTION("Stage1 YOLO 推理异常：%s", e)
        return False, [], None


def classify(pil_img, conf: float = 0.08):
    """
    单字识别（单减字释读 / 手动画框补识别）。

    单字图通常只有一个目标，故放宽置信度阈值，按最高分取 Top-3。

    返回：
        成功 -> (True, [(class_key, confidence), ...])
        失败 -> (False, [])
    """
    if not available():
        return False, []
    try:
        rgb = np.array(pil_img.convert("RGB"))[:, :, ::-1]   # RGB -> BGR
        raw = _raw_predict(rgb, conf, imgsz=224)
        if not raw:
            return True, []
        # 单字：只保留能对应注册表基础 key 的预测，按置信度聚合取 Top-3；
        # 模型细类标签映射不到 key 时一律视为本模型「不认识」，返回空列表，
        # 由上层（classifier）转多模态认字。
        best = {}
        for x1, y1, x2, y2, score, key, raw_name in raw:
            if not key:
                continue
            if key not in best or score > best[key]:
                best[key] = score
        if not best:
            return True, []
        ranked = sorted(best.items(), key=lambda kv: kv[1], reverse=True)[:3]
        ranked = [(k, round(float(c), 4)) for k, c in ranked]
        MLN_LOG_DEBUG("YOLO 单字识别：%s", ranked)
        return True, ranked
    except Exception as e:
        MLN_LOG_EXCEPTION("YOLO 单字推理异常，降级多模态/假数据：%s", e)
        return False, []


# ==============================================================================
# 古琴竖排排序：从右往左成列，列内从上到下
# ==============================================================================
def _sort_guqin(items: list) -> list:
    """
    按减字谱阅读顺序排序检测框。

    1. 先按 x1 从大到小（列从右到左）做稳定排序；
    2. 用聚类把相近 x1 归为同一列（列宽取框宽中位数，近 1/4 即同列）；
    3. 列内按 y1 从上到下。
    """
    if len(items) <= 1:
        return items

    def cx1(it):
        return it["box"]["x"]

    def cy1(it):
        return it["box"]["y"]

    widths = sorted(it["box"]["w"] for it in items)
    col_w = widths[len(widths) // 2] if widths else 0.1
    tol = max(col_w * 0.5, 0.02)

    # 按 x1 降序排，便于成列
    order = sorted(range(len(items)), key=lambda i: cx1(items[i]), reverse=True)

    columns = []          # 每列：list[原始 index]
    col_anchor = []       # 每列锚点 x1
    for idx in order:
        x = cx1(items[idx])
        placed = False
        for ci, anchor in enumerate(col_anchor):
            if abs(x - anchor) <= tol:
                columns[ci].append(idx)
                placed = True
                break
        if not placed:
            columns.append([idx])
            col_anchor.append(x)

    # 列仍按从右到左（锚点 x 降序）；列内从上到下
    col_order = sorted(range(len(columns)),
                       key=lambda c: col_anchor[c], reverse=True)
    sorted_idx = []
    for ci in col_order:
        sorted_idx.extend(sorted(columns[ci], key=lambda i: cy1(items[i])))

    return [items[i] for i in sorted_idx]
