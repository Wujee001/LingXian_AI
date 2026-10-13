# -*- coding: utf-8 -*-
"""
单减字分类器模块（三级降级：YOLO → 阿里云多模态 → 假数据）

predict_crop 对单个减字裁剪图给出 Top-3 候选：
    1. 优先本地 YOLO 权重（service/yolo_infer.py，离线、检测+分类一体）；
    2. YOLO 不可用时调用阿里云百炼多模态（service/qwen_adapter.py，
       密钥取环境变量 DASHSCOPE_API_KEY，免费额度用完即停）；
    3. 两者都失败时回退固定假数据，保证整谱/单字流程不中断。

接口形态始终为 [(class_key, confidence), ...]，上层与前端无需改动。
get_last_source() 返回本次实际命中的路线（yolo / qwen / fake），
便于接口回传给前端标注来源、写日志。

作者：
    @Wujee

更新日期：2026-10-13
版本：2.0.0（由 ResNet18 单模型改为统一三级降级入口）

许可证：内部使用，未经许可不得传播。

"""

from utils.mlnlog import MLN_LOG_INFO, MLN_LOG_WARN

# 本次实际命中的识别路线
_last_source = "fake"


def predict_crop(pil_img, engine: str = "auto"):
    """
    入参：
        pil_img：单个减字裁剪图（PIL.Image）
        engine：识别引擎，由用户在前端手动选择
            "auto" 自动：YOLO（能对应基础 key）→ 多模态 → 假数据
            "qwen" 多模态：强制跳过 YOLO，直接用阿里云多模态认字（当前更准）
            "yolo" 本地模型：仅用本地 YOLO，不联网/不耗额度，失败才回假数据
    返回：
        Top-3 候选 [(class_key, 置信度), ...]
    """
    global _last_source
    engine = (engine or "auto").strip().lower()

    # ---- 强制多模态 ----
    if engine == "qwen":
        if _predict_qwen(pil_img):
            _last_source = "qwen"
            return _predict_qwen._last
        _last_source = "fake"
        return _predict_fake()

    # ---- 强制本地 YOLO ----
    if engine == "yolo":
        ranked = _predict_yolo(pil_img)
        if ranked:
            _last_source = "yolo"
            return ranked
        _last_source = "fake"
        return _predict_fake()

    # ---- auto：YOLO 能认出基础 key 就用，否则多模态，再否则假数据 ----
    ranked = _predict_yolo(pil_img)
    if ranked:
        _last_source = "yolo"
        return ranked

    if _predict_qwen(pil_img):
        _last_source = "qwen"
        return _predict_qwen._last

    _last_source = "fake"
    return _predict_fake()


def _predict_yolo(pil_img):
    """本地 YOLO 分类，返回候选列表；不可用/认不出返回 []。"""
    try:
        from service import yolo_infer
        ok, ranked = yolo_infer.classify(pil_img)
        if ok and ranked:
            return ranked
    except Exception as e:
        MLN_LOG_WARN("YOLO 单字分类异常，尝试多模态：%s", e)
    return []


def _predict_qwen(pil_img) -> bool:
    """多模态分类；成功把结果挂到函数属性 _last，返回 True。"""
    try:
        from service import qwen_adapter
        ok, ranked = qwen_adapter.classify_crop(pil_img)
        if ok and ranked:
            _predict_qwen._last = ranked
            return True
    except Exception as e:
        MLN_LOG_WARN("多模态单字分类异常，回退假数据：%s", e)
    return False


_predict_qwen._last = []


def get_last_source() -> str:
    """返回最近一次 predict_crop 实际命中的路线：yolo / qwen / fake。"""
    return _last_source


def _predict_fake() -> list:
    """假模型兜底：固定 Top-3，仅用于权重/多模态都不可用时跑通闭环。"""
    return [
        ("da_9_gou_4", 0.82),
        ("san_tiao_7", 0.11),
        ("gou_5", 0.04),
    ]
