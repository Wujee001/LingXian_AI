# -*- coding: utf-8 -*-
"""
知识库接口：直接使用parser输出，分类正确，无需前端二次处理
"""
from fastapi import APIRouter, HTTPException, Query
from service.registry import all_classes
from service.parser import char_parse
from utils.mlnlog import MLN_LOG_INFO

router = APIRouter()
_lib = {}


def _build_full_lib():
    global _lib
    rows = all_classes(only_active=True)
    lib = {}
    for row in rows:
        key = row["class_key"]
        try:
            parse = char_parse(key)
        except Exception:
            continue
        item = {
            "char_key": key,
            "raw_key": key,
            "display": parse["display_name"],
            "type": parse["category"],
            "right_hand_text": parse["right_hand_text"],
            "left_hand_text": parse["left_hand_text"],
            "desc": parse["desc"],
            "is_san": parse["is_san"],
            "is_fan": parse["is_fan"],
        }
        lib[key] = item
    _lib = lib
    MLN_LOG_INFO("知识库构建完成，共%d条", len(lib))


_build_full_lib()


@router.get("/library")
def library(char_type: str = Query(None)):
    if char_type:
        items = {k: v for k, v in _lib.items() if v.get("type") == char_type}
    else:
        items = _lib
    return {"success": True, "count": len(items), "data": items}


@router.get("/detail/{char_key}")
def detail(char_key: str):
    item = _lib.get(char_key)
    if not item:
        raise HTTPException(status_code=404, detail=f"减字 {char_key} 未收录")
    return {"success": True, "data": item}


@router.get("/search")
def search(q: str = Query(..., min_length=1)):
    q_lower = q.lower()
    results = {}
    for key, item in _lib.items():
        haystack = " ".join([
            str(item.get("display", "")),
            str(item.get("type", "")),
            str(item.get("desc", "")),
        ]).lower()
        if q_lower in haystack or q_lower in key.lower():
            results[key] = item
    return {"success": True, "count": len(results), "data": results}


@router.get("/registry")
def registry():
    rows = all_classes()
    return {"success": True, "count": len(rows), "data": rows}
