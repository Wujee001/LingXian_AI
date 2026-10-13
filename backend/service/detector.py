# -*- coding: utf-8 -*-
"""
整谱减字检测模块

V1 使用 OpenCV 规则兜底：灰度→二值化→形态学→连通域，
框出整页减字谱中单个减字方块的大致位置，按古琴竖排
从右往左、从上到下排序。
V2 模型线 YOLO/RF-DETR 权重交付后，仅替换 detect() 内部，
上层接口与前端不动。

作者：
    @Wujee

创建日期：2026-10-1
版本：1.0.0

许可证：内部使用，未经许可不得传播。

"""

import cv2
import numpy as np

from utils.mlnlog import MLN_LOG_INFO, MLN_LOG_WARN


def detect(image_path: str) -> list:
    """
    检测整谱图中的减字方块。

    入参：
        image_path：整谱图片本地路径
    返回：
        list[dict]，每项 {x, y, w, h}，均为 0~1 归一化坐标
    """
    img = cv2.imread(image_path)
    if img is None:
        MLN_LOG_WARN("整谱图读取失败：%s", image_path)
        return []

    h, w = img.shape[:2]

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # 自适应阈值，适应墨色浓淡不均
    binary = cv2.adaptiveThreshold(
        gray, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        31, 15
    )

    # 闭运算，把同一减字内的笔画连成块
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (9, 9))
    closed = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel, iterations=2)

    num, labels, stats, _ = cv2.connectedComponentsWithStats(closed, connectivity=8)

    img_area = h * w
    boxes = []

    for i in range(1, num):
        x, y, bw, bh, area = stats[i]

        # 过滤噪点与跨整行/整页的大块
        if area < img_area * 0.002 or area > img_area * 0.12:
            continue
        if bw < w * 0.02 or bh < h * 0.02:
            continue

        # 减字方块宽高比接近 1
        ratio = bw / float(bh)
        if ratio < 0.45 or ratio > 1.8:
            continue

        boxes.append({
            "x": round(x / w, 5),
            "y": round(y / h, 5),
            "w": round(bw / w, 5),
            "h": round(bh / h, 5),
        })

    boxes = _sort_guqin_order(boxes)

    MLN_LOG_INFO("整谱规则检测完成，候选框数量：%d", len(boxes))
    return boxes


def _sort_guqin_order(boxes: list) -> list:
    """
    古琴减字谱竖排、从右往左、每列从上到下排序。

    先用 x 中心聚类成列，列内按 y 排序，列间按从右到左。
    """
    if not boxes:
        return boxes

    xs = np.array([b["x"] + b["w"] / 2 for b in boxes])
    med_w = float(np.median([b["w"] for b in boxes]))

    # 按 x 中心从右往左排序后贪心聚列
    order = np.argsort(-xs)
    columns = []
    for idx in order:
        cx = xs[idx]
        placed = False
        for col in columns:
            if abs(cx - col["cx"]) < med_w * 0.8:
                col["items"].append(boxes[idx])
                col["cx"] = np.mean(
                    [xs[boxes.index(it)] for it in col["items"]]
                )
                placed = True
                break
        if not placed:
            columns.append({"cx": cx, "items": [boxes[idx]]})

    columns.sort(key=lambda c: -c["cx"])

    result = []
    for col in columns:
        col["items"].sort(key=lambda b: b["y"])
        result.extend(col["items"])
    return result