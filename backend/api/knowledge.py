# -*- coding: utf-8 -*-
"""
知识库查询接口模块

提供减字语义知识库的 HTTP 查询接口：
- 列表浏览（可按散音/按音/泛音/装饰音/复合音筛选）
- 单个减字完整解析
- 模糊搜索（指法/弦/徽位/释义/拼音key）
- 类别主表导出

数据来源：core/jianzipu_lib.json（语义库）、data/class_registry.csv（类别主表）。
视觉模型只输出拼音 key，乐理解析全部由此模块对外提供。

作者：
    @Wujee

创建日期：2026-10-08
版本：1.0.0

许可证：内部使用，未经许可不得传播。

"""

import csv
import json
from pathlib import Path
from fastapi import APIRouter, HTTPException, Query
from utils.mlnlog import MLN_LOG_INFO, MLN_LOG_WARN, MLN_LOG_ERROR

router = APIRouter()

# 基于本文件位置定位数据文件，禁写死盘符
_CORE_DIR = Path(__file__).resolve().parent.parent / "core"
_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_LIB_PATH = _CORE_DIR / "jianzipu_lib.json"
_REGISTRY_PATH = _DATA_DIR / "class_registry.csv"

# 启动时加载到内存
_lib: dict = {}
_registry: list[dict] = []


def _load_lib():
    global _lib
    try:
        with open(_LIB_PATH, "r", encoding="utf-8") as f:
            _lib = json.load(f)
        MLN_LOG_INFO("知识库加载完成，共 %d 个减字", len(_lib))
    except Exception as e:
        MLN_LOG_ERROR("知识库加载失败: %s", e)
        _lib = {}


def _load_registry():
    global _registry
    try:
        with open(_REGISTRY_PATH, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            _registry = list(reader)
        MLN_LOG_INFO("类别主表加载完成，共 %d 类", len(_registry))
    except Exception as e:
        MLN_LOG_ERROR("类别主表加载失败: %s", e)
        _registry = []


_load_lib()
_load_registry()


@router.get("/library")
def library(char_type: str = Query(None, description="按类型筛选：散音/按音/泛音/装饰音/复合音")):
    """知识库列表，可按类型筛选"""
    if char_type:
        items = {k: v for k, v in _lib.items() if v.get("type") == char_type}
        MLN_LOG_INFO("查询知识库列表，类型=%s，结果=%d", char_type, len(items))
    else:
        items = _lib
        MLN_LOG_INFO("查询知识库列表，全部，结果=%d", len(items))
    return {"success": True, "count": len(items), "data": items}


@router.get("/detail/{char_key}")
def detail(char_key: str):
    """单个减字完整解析"""
    item = _lib.get(char_key)
    if not item:
        MLN_LOG_WARN("知识库未命中: %s", char_key)
        raise HTTPException(status_code=404, detail=f"减字 {char_key} 未收录")
    MLN_LOG_INFO("查询减字详情: %s", char_key)
    return {"success": True, "data": item}


@router.get("/search")
def search(q: str = Query(..., min_length=1, description="搜索关键词")):
    """模糊搜索：匹配 display / 指法 / 徽位 / 释义 / 拼音key"""
    q_lower = q.lower()
    results = {}
    for key, item in _lib.items():
        rh = item.get("right_hand") or {}
        lh = item.get("left_hand") or {}
        haystack = " ".join([
            str(item.get("display", "")),
            str(item.get("type", "")),
            str(item.get("meaning", "")),
            str(rh.get("finger", "")),
            str(lh.get("finger", "")),
        ]).lower()
        if q_lower in haystack or q_lower in key.lower():
            results[key] = item
    MLN_LOG_INFO("知识库搜索 q=%s，结果=%d", q, len(results))
    return {"success": True, "count": len(results), "data": results}


@router.get("/registry")
def registry():
    """类别主表（class_registry.csv）"""
    MLN_LOG_INFO("查询类别主表，共 %d 类", len(_registry))
    return {"success": True, "count": len(_registry), "data": _registry}