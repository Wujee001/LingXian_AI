# -*- coding: utf-8 -*-
"""
图像分类器模块

V1 假模型兜底：predict_crop 返回固定 Top-3 候选与置信度，
用于跑通整谱闭环。模型线 .pth 权重交付后，仅替换
predict_crop 内部（加载权重→预处理→推理），接口与前端不动。

作者：
    @Wujee

创建日期：2026-10-1
版本：1.0.0

许可证：内部使用，未经许可不得传播。

"""


def predict_crop(pil_img):
    """
    入参：
        pil_img：单个减字裁剪图（PIL.Image）
    返回：
        Top-3 候选 [(class_key, 置信度), ...]
    """
    return [
        ("san_gou3", 0.82),
        ("da9_gou4", 0.11),
        ("san_tiao2", 0.04),
    ]