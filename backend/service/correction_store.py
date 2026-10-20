# -*- coding: utf-8 -*-
"""
人工修正持久化服务（泠弦智谱 V1）

把整谱打谱页的人工确认/改判结果追加写入本地 JSON 文件
（backend/data/corrections.json），供模型线后续迭代训练使用。

V1 不引入数据库依赖，采用「单文件追加 + 线程锁」的轻量方案：
    - 每条记录含时间戳、谱图、框序号、归一化框、原识别 key、
      人工确认 key、来源路线；
    - 写操作全量读回-追加-落盘，数据量小时足够稳定；
    - 任何 IO 异常都只记录日志、不阻断前端交互。

作者：
    @Wujee

创建日期：2026-10-13
版本：1.0.0

许可证：内部使用，未经许可不得传播。

"""

import os
import json
import threading
from datetime import datetime

from core.config import DATA_DIR
from utils.mlnlog import MLN_LOG_INFO, MLN_LOG_EXCEPTION

_STORE_PATH = os.path.join(DATA_DIR, "corrections.json")
_lock = threading.Lock()


def _load_all() -> list:
    """读取全部修正记录；文件不存在或损坏时返回空列表。"""
    if not os.path.exists(_STORE_PATH):
        return []
    try:
        with open(_STORE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except Exception as e:
        MLN_LOG_EXCEPTION("修正记录读取失败，按空列表处理：%s", e)
        return []


def append(record: dict) -> int:
    """
    追加一条人工修正记录。

    入参：
        record：含 index/box/confirmed_key/origin_key/source/image_url 等字段
    返回：
        落库后记录总数。
    """
    with _lock:
        try:
            rows = _load_all()
            item = {
                "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "image_url": record.get("image_url"),
                "index": record.get("index"),
                "box": record.get("box"),
                "origin_key": record.get("origin_key"),
                "confirmed_key": record.get("confirmed_key"),
                "source": record.get("source"),
                "note": record.get("note"),
            }
            rows.append(item)
            os.makedirs(DATA_DIR, exist_ok=True)
            with open(_STORE_PATH, "w", encoding="utf-8") as f:
                json.dump(rows, f, ensure_ascii=False, indent=2)
            MLN_LOG_INFO("人工修正已落库：index=%s %s -> %s（累计 %d 条）",
                        item["index"], item["origin_key"],
                        item["confirmed_key"], len(rows))
            return len(rows)
        except Exception as e:
            MLN_LOG_EXCEPTION("人工修正落库失败：%s", e)
            return -1


def list_all() -> list:
    """返回全部修正记录（供后续导出/训练抽样）。"""
    with _lock:
        return _load_all()
