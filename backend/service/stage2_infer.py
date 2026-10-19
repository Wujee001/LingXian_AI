# -*- coding: utf-8 -*-
"""
Stage2 ResNet18 减字指法识别服务（两阶段架构第二级）

职责：对 Stage1 检测出的每个减字框裁剪图，识别输出八字段属性：
右手指法、弦位、左手指法、徽位、修饰音等，再组合成标准减字候选。

作者：
    @Wujee
创建日期：2026-10-19
版本：2.0.0
"""
import os
from pathlib import Path
import torch
from PIL import Image
from torchvision import transforms
from torchvision.models import resnet18
from torch import nn

from core.config import MODEL_DIR
from utils.mlnlog import MLN_LOG_INFO, MLN_LOG_WARN, MLN_LOG_EXCEPTION, MLN_LOG_DEBUG

_WEIGHT_PATH = os.path.join(MODEL_DIR, "stage2_best.pth")
_model = None
_vocab = None
_imgsz = 96
_ready = False
_checked = False

HEADS = ('rh', 'string', 'lh', 'hui_base', 'hui_frac', 'mod', 'tone', 'strings')


class MultiHeadResNet(nn.Module):
    def __init__(self, vocab):
        super().__init__()
        backbone = resnet18(weights=None)
        dim = backbone.fc.in_features
        backbone.fc = nn.Identity()
        self.backbone = backbone
        self.heads = nn.ModuleDict({
            h: nn.Sequential(nn.Dropout(0.3), nn.Linear(dim, len(vocab[h])))
            for h in HEADS
        })

    def forward(self, x):
        features = self.backbone(x)
        return {h: head(features) for h, head in self.heads.items()}


def available() -> bool:
    global _checked
    if not _checked:
        _ensure_model()
    return _ready


def _ensure_model():
    global _model, _vocab, _imgsz, _ready, _checked
    if _checked:
        return _ready
    _checked = True

    if not os.path.exists(_WEIGHT_PATH):
        MLN_LOG_WARN("未发现 Stage2 ResNet18 权重 %s，单字分类将走多模态兜底", _WEIGHT_PATH)
        _ready = False
        return False
    try:
        ckpt = torch.load(_WEIGHT_PATH, map_location='cpu', weights_only=True)
        _vocab = ckpt['vocab']
        _imgsz = int(ckpt['imgsz'])
        net = MultiHeadResNet(_vocab)
        net.load_state_dict(ckpt['state_dict'], strict=True)
        net.eval()
        _model = net
        _ready = True
        MLN_LOG_INFO("Stage2 ResNet18 权重加载成功：%s", _WEIGHT_PATH)
        return True
    except Exception as e:
        MLN_LOG_EXCEPTION("Stage2 ResNet18 权重加载失败：%s", e)
        _model, _ready = None, False
        return False


_transform = transforms.Compose([
    transforms.Grayscale(num_output_channels=3),
    transforms.Resize((96, 96)),
    transforms.ToTensor(),
    transforms.Normalize((.485, .456, .406), (.229, .224, .225)),
])


def predict_crop(pil_img: Image.Image):
    """对单张减字裁剪图识别，返回 Top1 减字key与置信度。"""
    if not available():
        return False, []
    try:
        tensor = _transform(pil_img.convert('L')).unsqueeze(0)
        with torch.no_grad():
            out = _model(tensor)
        attrs = {}
        confs = []
        for head in HEADS:
            probs = torch.softmax(out[head][0], dim=0)
            conf, idx = torch.max(probs, dim=0)
            attrs[head] = _vocab[head][idx.item()]
            confs.append(float(conf))
        avg_conf = sum(confs) / len(confs)
        key = f"{attrs.get('rh','')}_{attrs.get('string','')}_{attrs.get('lh','')}_{attrs.get('hui_base','')}_{attrs.get('hui_frac','')}"
        MLN_LOG_DEBUG("Stage2 识别结果：%s 置信度 %.3f", key, avg_conf)
        return True, [(key, round(avg_conf, 4))]
    except Exception as e:
        MLN_LOG_EXCEPTION("Stage2 单框识别异常：%s", e)
        return False, []
