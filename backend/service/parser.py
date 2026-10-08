# -*- coding: utf-8 -*-
"""
减字解析模块

将分类器输出的 class_key（拼音编码）翻译为可读演奏信息：
左手手指/徽位、右手指法/弦号、释义。优先读取
core/jianzipu_lib.json 知识库，未收录时返回占位结构，
不阻断整谱流程。乐理全部在此与知识库中处理，视觉模型
只输出 class_key（视觉与乐理分离）。

作者：
    @Wujee

创建日期：2026-10-1
版本：1.0.0

许可证：内部使用，未经许可不得传播。

"""

import json
import os

from core.config import BACKEND_ROOT
from utils.mlnlog import MLN_LOG_INFO, MLN_LOG_WARN

# 减字语义知识库
_LIB_PATH = os.path.join(BACKEND_ROOT, "core", "jianzipu_lib.json")


def _load_lib() -> dict:
    """读取减字知识库，文件缺失或格式错误时返回空字典。"""
    try:
        with open(_LIB_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def char_parse(class_key: str) -> dict:
    """
    入参：
        class_key：减字拼音编码，如 da_9_gou_4
    返回：
        演奏解析 {class_key, display_name, left_hand, right_hand, meaning}
    """
    lib = _load_lib()
    item = lib.get(class_key)

    if item is None:
        MLN_LOG_WARN("知识库未收录减字：%s，返回占位", class_key)
        return {
            "class_key": class_key,
            "display_name": class_key,
            "left_hand": {},
            "right_hand": {},
            "meaning": "暂未收录该减字释义",
        }

    MLN_LOG_INFO("解析减字：%s", class_key)
    return {"class_key": class_key, **item}