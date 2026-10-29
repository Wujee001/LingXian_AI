# -*- coding: utf-8 -*-
"""
知识库查询接口模块

提供减字语义知识库的 HTTP 查询接口：
- 列表浏览（可按散音/按音/泛音/装饰音/复合音筛选）
- 单个减字完整解析
- 模糊搜索（指法/弦/徽位/释义/拼音key）
- 类别主表导出（统一由 service.registry 加载，避免重复解析 CSV）

数据来源：core/jianzipu_lib.json（语义库）、service.registry（类别主表）。
视觉模型只输出拼音 key，乐理解析全部由此模块对外提供。

作者：
    @Wujee

创建日期：2026-10-08
版本：1.1.0（2026-10-27 @zjx：合并318类目录与25条已有详细释义）

许可证：内部使用，未经许可不得传播。

"""

from fastapi import APIRouter, HTTPException, Query

from service.knowledge_catalog import get_knowledge, list_knowledge, knowledge_counts
from service.registry import all_classes
from utils.mlnlog import MLN_LOG_INFO, MLN_LOG_WARN

router = APIRouter()


@router.get("/library")
def library(char_type: str | None = Query(None, description="按原有音类、候选类型或候选/已有详情筛选")):
    """默认显示318条；新增293条仅为候选，不伪称有完整释义。"""
    catalog = list_knowledge()
    if char_type == "待复核":
        catalog = {k: v for k, v in catalog.items() if v["knowledge_status"] == "registry_candidate"}
    elif char_type == "已有释义":
        catalog = {k: v for k, v in catalog.items() if v["knowledge_status"] == "legacy_detail"}
    elif char_type:
        catalog = {k: v for k, v in catalog.items() if v.get("type") == char_type}
    MLN_LOG_INFO("查询减字目录：类型=%s，结果=%d", char_type or "全部", len(catalog))
    return {"success": True, "count": len(catalog), "data": catalog}


@router.get("/detail/{char_key}")
def detail(char_key: str):
    item = get_knowledge(char_key)
    if item is None:
        MLN_LOG_WARN("类别目录未登记：%s", char_key)
        raise HTTPException(status_code=404, detail=f"类别 {char_key} 未登记")
    return {"success": True, "data": item}


@router.get("/search")
def search(q: str = Query(..., min_length=1, description="搜索 key、名称、演奏释义")):
    query = q.strip().lower()
    catalog = list_knowledge()
    results = {}
    for key, item in catalog.items():
        rh = item.get("right_hand") or {}
        lh = item.get("left_hand") or {}
        haystack = " ".join([
            key, str(item.get("display", "")), str(item.get("type", "")),
            # 通用的「待复核」占位描述不可进入搜索，否则搜索「复」会命中全部候选。
            str(item.get("meaning", "")) if item.get("knowledge_status") != "registry_candidate" else "",
            str(rh.get("finger", "")), str(lh.get("finger", "")),
        ]).lower()
        if query in haystack:
            results[key] = item
    MLN_LOG_INFO("减字目录搜索 q=%s，结果=%d", q, len(results))
    return {"success": True, "count": len(results), "data": results}


@router.get("/registry")
def registry():
    rows = all_classes()
    return {"success": True, "count": len(rows), "data": rows}


@router.get("/coverage")
def coverage():
    """明确区分目录覆盖与详细释义覆盖，不将318条误称为知识库已完成。"""
    return {"success": True, "data": knowledge_counts()}
