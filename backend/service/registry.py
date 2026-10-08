# -*- coding: utf-8 -*-
"""
类别注册表加载模块

统一加载 backend/data/class_registry.csv 类别主表，提供按
class_key / class_id / category 查询、启用类别过滤，带缓存。
软件线与模型线共用此表，禁止他处自行解析 CSV。

作者：
    @Wujee

创建日期：2026-10-08
版本：1.0.0

许可证：内部使用，未经许可不得传播。

"""

import csv
import os
import threading

from utils.mlnlog import MLN_LOG_INFO, MLN_LOG_EXCEPTION

# 本文件位于 backend/service/registry.py，回溯两级到 backend
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGISTRY_CSV = os.path.join(_BACKEND_DIR, "data", "class_registry.csv")

_lock = threading.Lock()
_cache = None


def _to_bool(value) -> bool:
    return str(value).strip() in ("1", "true", "True", "yes")


def _load() -> list:
    """读取 CSV 并缓存，返回类别记录列表。"""
    global _cache
    if _cache is not None:
        return _cache
    with _lock:
        if _cache is None:
            rows = []
            # utf-8-sig 兼容带 BOM 的 CSV
            with open(REGISTRY_CSV, "r", encoding="utf-8-sig", newline="") as f:
                for r in csv.DictReader(f):
                    if not r.get("class_key"):
                        continue
                    rows.append({
                        "class_id": int(r["class_id"]),
                        "class_key": r["class_key"].strip(),
                        "display_name": r["display_name"].strip(),
                        "category": r["category"].strip(),
                        "active": _to_bool(r.get("active")),
                    })
            _cache = rows
            MLN_LOG_INFO("类别注册表加载完成，共 %d 类", len(rows))
    return _cache


def all_classes(only_active: bool = False) -> list:
    """全量类别；only_active=True 仅返回启用类别。"""
    rows = _load()
    return [r for r in rows if r["active"]] if only_active else rows


def get_by_key(class_key: str):
    """按拼音 key 查单类，未命中返回 None。"""
    for r in _load():
        if r["class_key"] == class_key:
            return r
    return None


def get_by_id(class_id: int):
    """按数字 class_id 查单类，未命中返回 None。"""
    for r in _load():
        if r["class_id"] == class_id:
            return r
    return None


def keys_by_category(category: str, only_active: bool = True) -> list:
    """按类别归属（single/modifier_only/compound）筛选。"""
    return [r for r in _load()
            if r["category"] == category and (r["active"] or not only_active)]


def active_keys() -> list:
    """全部启用类别的拼音 key，供模型/校验对齐。"""
    return [r["class_key"] for r in _load() if r["active"]]


def reload() -> list:
    """清除缓存重新加载（CSV 更新后调用）。"""
    global _cache
    with _lock:
        _cache = None
    return _load()