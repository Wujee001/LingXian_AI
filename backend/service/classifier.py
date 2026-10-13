# -*- coding: utf-8 -*-
"""
图像分类器模块（真权重优先，假模型兜底）

predict_crop 首次调用时懒加载真实权重：
    1. 检测 backend/models/resnet18_qin.pth 是否存在；
    2. 存在则用 torchvision 构建 ResNet18（末层改为注册表类别数），
       加载权重，按 ImageNet 规格预处理（224/RGB/归一化）后推理；
    3. 类别索引→class_key 优先读 models/class_mapping.json，
       缺失时回退 class_registry.csv 的 class_id 顺序；
    4. 任一环节失败（未装 torch、无权重、权重损坏、类别数不符）
       一律记录日志并回退固定假数据，保证整谱/单字流程不中断。

模型线 .pth 交付后只需把权重与 class_mapping.json 放进
backend/models/，无需改动本文件接口与前端。

作者：
    @Wujee

更新日期：2026-10-12
版本：1.1.0

许可证：内部使用，未经许可不得传播。

"""

import os
import json

from core.config import MODEL_DIR
from utils.mlnlog import MLN_LOG_INFO, MLN_LOG_WARN, MLN_LOG_EXCEPTION

# 单字分类权重与类别映射（.gitignore 已忽略，走 GitHub Release）
_WEIGHT_PATH = os.path.join(MODEL_DIR, "resnet18_qin.pth")
_MAPPING_PATH = os.path.join(MODEL_DIR, "class_mapping.json")

# ResNet18 迁移学习标准输入
_INPUT_SIZE = 224
_IMAGENET_MEAN = [0.485, 0.456, 0.406]
_IMAGENET_STD = [0.229, 0.224, 0.225]

# 真实模型运行期单例（懒加载）
_model = None
_transform = None
_idx_to_key = None
_real_ready = False
_checked = False


def predict_crop(pil_img):
    """
    入参：
        pil_img：单个减字裁剪图（PIL.Image）
    返回：
        Top-3 候选 [(class_key, 置信度), ...]
    说明：
        真实权重可用则走模型推理，否则回退假模型，接口形态不变。
    """
    if _ensure_model():
        try:
            return _predict_real(pil_img)
        except Exception as e:
            MLN_LOG_EXCEPTION("真实模型推理异常，本次回退假模型：%s", e)
    return _predict_fake()


def _ensure_model() -> bool:
    """
    懒加载真实权重，全程只检测一次。

    返回：
        True 表示真实模型就绪；False 表示应使用假模型兜底。
    """
    global _model, _transform, _idx_to_key, _real_ready, _checked
    if _checked:
        return _real_ready
    _checked = True

    if not os.path.exists(_WEIGHT_PATH):
        MLN_LOG_WARN("未发现权重文件 %s，单字识别使用假模型兜底", _WEIGHT_PATH)
        return False

    try:
        import torch
        import torch.nn as nn
        from torchvision import models, transforms

        idx_to_key = _build_idx_mapping()
        class_num = len(idx_to_key)
        if class_num == 0:
            MLN_LOG_WARN("类别映射为空，无法构建模型，回退假模型")
            return False

        # ResNet18 迁移学习：替换末层全连接为当前类别数
        net = models.resnet18(weights=None)
        net.fc = nn.Linear(net.fc.in_features, class_num)

        state = torch.load(_WEIGHT_PATH, map_location="cpu")
        # 兼容裸 state_dict 与 {'state_dict': ...} / {'model': ...} 两种导出
        if isinstance(state, dict):
            state = state.get("state_dict", state.get("model", state))
        net.load_state_dict(state)
        net.eval()

        _transform = transforms.Compose([
            transforms.Resize(256),
            transforms.CenterCrop(_INPUT_SIZE),
            transforms.ToTensor(),
            transforms.Normalize(mean=_IMAGENET_MEAN, std=_IMAGENET_STD),
        ])
        _model = net
        _idx_to_key = idx_to_key
        _real_ready = True
        MLN_LOG_INFO("真实分类权重加载成功：%s（%d 类）", _WEIGHT_PATH, class_num)
        return True
    except Exception as e:
        MLN_LOG_EXCEPTION("真实权重加载失败，回退假模型：%s", e)
        _model, _transform, _idx_to_key = None, None, None
        _real_ready = False
        return False


def _build_idx_mapping() -> dict:
    """
    构建模型输出索引 → class_key 映射。

    优先读取 class_mapping.json，兼容三种常见格式：
        ["key0", "key1"]（列表下标即索引）
        {"0": "key0", ...}（字符串/数字键）
        [{"class_id": 0, "class_key": "key0"}, ...]
    文件缺失时回退 class_registry.csv 中启用类别、按 class_id 排序。
    """
    if os.path.exists(_MAPPING_PATH):
        try:
            with open(_MAPPING_PATH, "r", encoding="utf-8") as f:
                raw = json.load(f)
            mapping = {}
            if isinstance(raw, list):
                for i, item in enumerate(raw):
                    if isinstance(item, str):
                        mapping[i] = item
                    elif isinstance(item, dict):
                        mapping[int(item.get("class_id", i))] = item.get("class_key")
            elif isinstance(raw, dict):
                for k, v in raw.items():
                    mapping[int(k)] = v
            MLN_LOG_INFO("加载 class_mapping.json，共 %d 类", len(mapping))
            return mapping
        except Exception as e:
            MLN_LOG_EXCEPTION("class_mapping.json 解析失败，改用注册表：%s", e)

    # 回退：注册表启用类别按 class_id 升序
    from service.registry import all_classes
    rows = sorted(all_classes(only_active=True), key=lambda r: r["class_id"])
    mapping = {r["class_id"]: r["class_key"] for r in rows}
    MLN_LOG_INFO("未提供 class_mapping.json，按注册表生成 %d 类映射", len(mapping))
    return mapping


def _predict_real(pil_img) -> list:
    """真实模型推理，返回 Top-3 [(class_key, 置信度), ...]。"""
    import torch

    x = _transform(pil_img.convert("RGB")).unsqueeze(0)
    with torch.no_grad():
        logits = _model(x)
        probs = torch.softmax(logits, dim=1)[0]

    k = min(3, probs.numel())
    top_vals, top_idx = torch.topk(probs, k=k)

    result = []
    for val, idx in zip(top_vals.tolist(), top_idx.tolist()):
        key = _idx_to_key.get(idx, str(idx))
        result.append((key, round(float(val), 4)))
    return result


def _predict_fake() -> list:
    """假模型兜底：固定 Top-3，仅用于权重交付前跑通闭环。"""
    return [
        ("da_9_gou_4", 0.82),
        ("san_tiao_7", 0.11),
        ("gou_5", 0.04),
    ]