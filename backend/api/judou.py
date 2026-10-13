# -*- coding: utf-8 -*-
"""
智能句读接口模块（泠弦智谱 V1）

输入减字 class_key 序列，返回逐字边界标签（C连续/S短停/L长停/E句末/U复核）
与置信度。两级实现：
    1. 优先阿里云百炼多模态（service/qwen_adapter.py，纯文本），
       让模型依据古琴乐理综合指法、散按交替、复音与走音给出边界；
    2. 多模态不可用（无密钥/额度耗尽/超时）时回退内置假规则
       （每8字E、每4字S、其余C），保证页面可独立演示。

modules 下的状态转移/句读规则/序列决策算法模块（V2 有标注数据集后）
就绪后，仅替换本文件内部实现，接口与前端不动。

作者：
    @Wujee

更新日期：2026-10-13
版本：2.0.0

许可证：内部使用，未经许可不得传播。

"""

from fastapi import APIRouter
from pydantic import BaseModel

from utils.mlnlog import MLN_LOG_INFO, MLN_LOG_EXCEPTION

router = APIRouter()

# 低于该置信度标记为 U 人工复核
CONFIDENCE_TAU = 0.6

# 多模态命中间隔标签的默认置信度
_LABEL_CONF = {"C": 0.85, "S": 0.8, "L": 0.8, "E": 0.82, "U": 0.5}


class SegmentReq(BaseModel):
    chars: list[str]


@router.post("/segment")
async def segment(req: SegmentReq):
    """输入减字序列，返回逐字句读边界标签。"""
    try:
        chars = req.chars or []
        n = len(chars)

        labels, source = _segment_labels(chars)

        results = []
        for i, key in enumerate(chars):
            label = labels[i]
            conf = _LABEL_CONF.get(label, 0.8)
            if conf < CONFIDENCE_TAU:
                label = "U"
            results.append({
                "index": i,
                "class_key": key,
                "label": label,
                "confidence": conf,
            })

        MLN_LOG_INFO("句读分段（%s）：输入 %d 字，输出 %d 条标签",
                     source, n, len(results))

        return {
            "success": True,
            "data": {
                "count": n,
                "source": source,
                "segments": results,
            },
        }
    except Exception as e:
        MLN_LOG_EXCEPTION("句读分段异常：%s", e)
        return {"success": False, "data": {"msg": f"分段失败：{e}"}}


def _segment_labels(chars: list):
    """
    返回 (labels, source)。
    优先多模态；失败回退假规则（每8字E、每4字S、其余C）。
    """
    try:
        from service import qwen_adapter
        ok, labels = qwen_adapter.segment(chars)
        if ok and labels:
            return labels, "qwen"
    except Exception as e:
        MLN_LOG_INFO("多模态句读不可用，回退假规则：%s", e)

    fake = []
    for i in range(len(chars)):
        if (i + 1) % 8 == 0:
            fake.append("E")
        elif (i + 1) % 4 == 0:
            fake.append("S")
        else:
            fake.append("C")
    return fake, "fake"
