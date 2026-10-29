# -*- coding: utf-8 -*-
"""泠弦智谱：统一的减字目录与释义读取入口。

原有 jianzipu_lib.json 提供已有详细释义；class_registry.csv 提供类别目录。
CSV 仅含名称、类别等，不能据此推断左右手动作或生成已审核详细释义。

新增：@zjx
日期：2026-10-27
版本：1.0.0
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from service.registry import all_classes, get_by_key

_LIB_PATH = Path(__file__).resolve().parents[1] / "core" / "jianzipu_lib.json"
_CANDIDATE_TYPES = {
    "single": "单字候选",
    "compound": "复合候选",
    "modifier_only": "技法候选",
}


@lru_cache(maxsize=1)
def _legacy_library() -> dict:
    """缺失/损坏时抛出异常，防止悄悄把25条详细释义降成候选。"""
    with _LIB_PATH.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("jianzipu_lib.json 应为以 class_key 为键的对象")
    return data


def _entry_from_row(row: dict, library: dict) -> dict:
    key = row["class_key"]
    item = library.get(key)
    if item is not None:
        # 原有词条原样保存释义字段，只增加目录元数据。它不等于本次专家验收。
        result = dict(item)
        result.setdefault("char_key", key)
        result.setdefault("display", row["display_name"])
        result.setdefault("type", _CANDIDATE_TYPES.get(row["category"], "未知类别"))
        result["class_id"] = row["class_id"]
        result["category"] = row["category"]
        result["knowledge_status"] = "legacy_detail"
        result["needs_meaning_review"] = False
        return result

    name = row["display_name"]
    return {
        "char_key": key,
        "class_id": row["class_id"],
        "display": name,
        "display_name": name,
        "category": row["category"],
        "type": _CANDIDATE_TYPES.get(row["category"], "未分类候选"),
        "left_hand": None,
        "right_hand": None,
        # None=未审核/未知，不能擅自把未知音类默认显示成按音或散音。
        "is_san": None,
        "is_fan": None,
        "meaning": f"类别目录已登记「{name}」，尚缺按原始减字标注核验的完整指法释义，待人工复核。",
        "knowledge_status": "registry_candidate",
        "needs_meaning_review": True,
    }


def list_knowledge() -> dict:
    """保留CSV顺序，返回318项目录；其中仅25条来自已有详细词条。"""
    library = _legacy_library()
    rows = all_classes()
    return {row["class_key"]: _entry_from_row(row, library) for row in rows}


def get_knowledge(class_key: str) -> dict | None:
    """只支持精确 key；未知 key 由调用方明确返回404或未登记。"""
    key = str(class_key or "").strip()
    if not key:
        return None
    row = get_by_key(key)
    if row is None:
        return None
    return _entry_from_row(row, _legacy_library())


def knowledge_counts() -> dict:
    catalog = list_knowledge()
    detailed = sum(1 for item in catalog.values() if item["knowledge_status"] == "legacy_detail")
    return {"total": len(catalog), "legacy_detail": detailed, "registry_candidate": len(catalog) - detailed}
