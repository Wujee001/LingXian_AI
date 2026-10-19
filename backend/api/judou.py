# -*- coding: utf-8 -*-
"""
智能句读接口（纯本地规则引擎，V1版，无云API）
依据古琴传统句读规则：
1. 复合长指法（撮/拨/轮/打圆/滚拂/多弦组合）为乐句结束点
2. 走手音结束（带起/抓起/掐起/应合/撞）为短停顿点
3. 散按交替切换位置为短停顿
4. 兜底：连续4单音短停，连续8单音句末长停
V2再基于标注数据集训练专属句读模型。
"""
from fastapi import APIRouter
from pydantic import BaseModel
from utils.mlnlog import MLN_LOG_INFO, MLN_LOG_EXCEPTION

router = APIRouter()
CONFIDENCE_TAU = 0.6
# 标签置信度
_LABEL_CONF = {
    "C": 0.85,   # 连续
    "S": 0.78,   # 短停
    "L": 0.75,   # 长停
    "E": 0.82,   # 句末
    "U": 0.5
}

# 句末长停顿指法（右手复合长音）
LONG_END_FINGERS = {"cuo", "bo", "lun", "da_yuan", "li"}
# 短停顿修饰音（走手音结束）
SHORT_END_MODS = {"daiqi", "zhuaqi", "qia_qi", "yinghe", "zhuang", "zhu", "fu"}


class SegmentReq(BaseModel):
    chars: list[str]


@router.post("/segment")
async def segment(req: SegmentReq):
    try:
        chars = req.chars or []
        n = len(chars)
        if n == 0:
            return {"success": True, "data": {"count": 0, "segments": []}}

        labels = _rule_segment(chars)
        results = []
        for i, key in enumerate(chars):
            label = labels[i]
            conf = _LABEL_CONF.get(label, 0.8)
            results.append({
                "index": i,
                "class_key": key,
                "label": label,
                "confidence": conf,
            })
        MLN_LOG_INFO("本地规则句读完成：输入%d字，输出%d条", n, len(results))
        return {
            "success": True,
            "data": {
                "count": n,
                "source": "local_rule",
                "segments": results,
            },
        }
    except Exception as e:
        MLN_LOG_EXCEPTION("句读异常：%s", e)
        return {"success": False, "data": {"msg": "句读失败，请联系开发人员检查"}}


def _rule_segment(chars: list):
    """
    纯规则句读：
    输入为Stage2输出的组合key，格式：rh_string_lh_hui_base_hui_frac
    """
    labels = []
    last_tone = None
    continuous_count = 0

    for i, key in enumerate(chars):
        parts = str(key).split("_")
        rh = parts[0] if len(parts) > 0 else ""
        mod = parts[-1] if len(parts) > 5 else ""

        # 1. 句末长停顿：复合长指法
        if rh in LONG_END_FINGERS:
            labels.append("E")
            continuous_count = 0
            continue

        # 2. 短停顿：走手结束修饰音
        if mod in SHORT_END_MODS:
            labels.append("S")
            continuous_count = 0
            continue

        # 3. 兜底规则：连续计数
        continuous_count += 1
        if continuous_count % 8 == 0:
            labels.append("E")
            continuous_count = 0
        elif continuous_count % 4 == 0:
            labels.append("S")
        else:
            labels.append("C")

    # 最后一个字强制句末停顿
    if labels:
        labels[-1] = "E"
    return labels
