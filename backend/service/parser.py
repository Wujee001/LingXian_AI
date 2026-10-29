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
版本：1.1.0（2026-10-27 @zjx：新增注册表候选回退，不伪造释义）

许可证：内部使用，未经许可不得传播。

"""

from service.knowledge_catalog import get_knowledge
from utils.mlnlog import MLN_LOG_INFO, MLN_LOG_WARN


def char_parse(class_key: str) -> dict:
    """原有25条返回详细释义，其余注册表记录只返回待复核候选。"""
    item = get_knowledge(class_key)
    if item is not None:
        if item["knowledge_status"] == "registry_candidate":
            MLN_LOG_WARN("减字已列目录但详细释义待核：%s", class_key)
        else:
            MLN_LOG_INFO("解析已有知识词条：%s", class_key)
        return item

    MLN_LOG_WARN("减字类别未登记：%s", class_key)
    return {
        "class_key": class_key,
        "display_name": str(class_key),
        "left_hand": None,
        "right_hand": None,
        "meaning": "该 class_key 尚未登记，请核对识别结果或人工选择类别。",
        "knowledge_status": "unknown_key",
        "needs_meaning_review": True,
    }
