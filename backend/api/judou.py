# -*- coding: utf-8 -*-
"""
智能句读接口模块

V1 假模型兜底：输入减字 class_key 序列，返回逐字边界标签
（C连续/S短停/L长停/E句末）与置信度，低置信标 U 人工复核。
modules 算法模块（状态转移+句读规则+序列决策）就绪后，
仅替换 segment 内部调用，接口与前端不动。

作者：
    @Wujee

创建日期：2026-10-08
版本：1.0.0

许可证：内部使用，未经许可不得传播。

"""

from fastapi import APIRouter
from pydantic import BaseModel

from utils.mlnlog import MLN_LOG_INFO, MLN_LOG_EXCEPTION

router = APIRouter()

# 低于该置信度标记为 U 人工复核
CONFIDENCE_TAU = 0.6


class SegmentReq(BaseModel):
    chars: list[str]


@router.post("/segment")
async def segment(req: SegmentReq):
    """输入减字序列，返回逐字句读边界标签。"""
    try:
        n = len(req.chars)
        results = []

        for i, key in enumerate(req.chars):
            # 假模型：每8字一句(E)，每4字一短停(S)，其余连续(C)
            if (i + 1) % 8 == 0:
                label, conf = "E", 0.78
            elif (i + 1) % 4 == 0:
                label, conf = "S", 0.71
            else:
                label, conf = "C", 0.85

            if conf < CONFIDENCE_TAU:
                label = "U"

            results.append({
                "index": i,
                "class_key": key,
                "label": label,
                "confidence": conf,
            })

        MLN_LOG_INFO("句读分段：输入 %d 字，输出 %d 条标签", n, len(results))

        return {
            "success": True,
            "data": {
                "count": n,
                "segments": results,
            },
        }
    except Exception as e:
        MLN_LOG_EXCEPTION("句读分段异常：%s", e)
        return {"success": False, "data": {"msg": f"分段失败：{e}"}}