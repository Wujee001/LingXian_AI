# -*- coding: utf-8 -*-
"""
减字解析模块：自动归一化Stage2输出key，匹配知识库
"""
import json
import os
from core.config import CORE_DIR
from utils.mlnlog import MLN_LOG_INFO

_LIB_PATH = os.path.join(CORE_DIR, "jianzipu_lib.json")
_LIB_CACHE = None


def _load_lib():
    global _LIB_CACHE
    if _LIB_CACHE is not None:
        return _LIB_CACHE
    if not os.path.exists(_LIB_PATH):
        _LIB_CACHE = {}
        return _LIB_CACHE
    with open(_LIB_PATH, "r", encoding="utf-8") as f:
        _LIB_CACHE = json.load(f)
    MLN_LOG_INFO("知识库加载完成，共 %d 个减字", len(_LIB_CACHE))
    return _LIB_CACHE


_load_lib()


def _normalize_key(raw: str) -> str:
    """
    归一化Stage2输出的5段key：rh_string_lh_huiBase_huiFrac
    转成知识库标准key
    """
    raw = str(raw)
    parts = raw.split("_")
    # 已经是标准key直接返回
    if raw in _load_lib():
        return raw
    if len(parts) != 5:
        return raw

    rh, string, lh, hui_base, hui_frac = parts
    lh = None if lh.upper() == "NA" else lh
    hui_base = None if hui_base.upper() == "NA" else hui_base
    hui_frac = None if hui_frac.upper() == "NA" or hui_frac == "0" else hui_frac

    # 散音：无左手
    if lh is None or hui_base is None:
        return f"{rh}_{string}"
    # 按音，带分数徽位
    if hui_frac:
        return f"{lh}_{hui_base}_{hui_frac}_{rh}_{string}"
    # 普通按音
    return f"{lh}_{hui_base}_{rh}_{string}"


def char_parse(raw_key: str) -> dict:
    raw_key = str(raw_key)
    norm_key = _normalize_key(raw_key)
    lib = _load_lib()

    if norm_key in lib:
        item = lib[norm_key]
        rh = item.get("right_hand")
        lh = item.get("left_hand")
        rh_text = "—"
        lh_text = "—"
        if rh:
            rh_text = f"{rh.get('finger','')} · {rh.get('string','')}弦"
        if lh:
            hui = lh.get('hui','')
            lh_text = f"{lh.get('finger','')}{hui}徽"
        if item.get("is_san"):
            lh_text = "散音（不按弦）"
        if item.get("is_fan"):
            lh_text = f"轻点{lh.get('hui','')}徽"
        return {
            "raw_key": norm_key,
            "display_name": item.get("display", norm_key),
            "category": item.get("type", "其他"),
            "right_hand_text": rh_text,
            "left_hand_text": lh_text,
            "desc": item.get("meaning", ""),
            "is_san": item.get("is_san", False),
            "is_fan": item.get("is_fan", False),
            "right_hand": rh,
            "left_hand": lh,
            "meaning": item.get("meaning", "")
        }

    MLN_LOG_INFO("未收录：%s（归一后%s）", raw_key, norm_key)
    return {
        "raw_key": norm_key,
        "display_name": "未收录",
        "category": "未识别",
        "right_hand_text": "—",
        "left_hand_text": "—",
        "desc": "该减字暂未收录，请联系开发人员补充。",
        "is_san": False,
        "is_fan": False,
        "right_hand": None,
        "left_hand": None,
        "meaning": "该减字暂未收录，请联系开发人员补充。"
    }
