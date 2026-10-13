# -*- coding: utf-8 -*-
"""
阿里云百炼多模态适配服务（泠弦智谱 V1 第二级兜底）

当本地 YOLO 权重不可用（未装 ultralytics / 无权重 / 推理异常）时，
调用阿里云百炼多模态大模型进行零样本识别：
    - 单字识别：把裁剪图发给多模态模型，让它从注册表 25 类候选中
      选出最匹配的减字（输出 class_key）；
    - 智能句读：纯文本输入（减字序列），让模型按古琴乐理标 C/S/L/E/U。

设计要点：
    1. 密钥只从环境变量 DASHSCOPE_API_KEY 读取，绝不硬编码、不回显；
    2. 默认模型 qwen3-omni-flash（全模态视觉对话，实测图像/文本 1~2s），
       可用环境变量 QWEN_MODEL 切换；qwen3.8-omni-flash 偏慢留作备选；
       qwen-mt-uni 为翻译模型，不能用于视觉理解；
    3. 走 OpenAI 兼容端点，用标准库 urllib，零额外依赖（不强制装 requests）；
    4. 免费额度开启「用完即停」，耗尽时返回 HTTP 403 /
       AllocationQuota.FreeTierOnly，本模块捕获后熔断，后续直接快速失败，
       由上层走假数据，不产生任何费用；
    5. 无 key / 超时 / 网络异常 / 返回非法 JSON，一律安全降级。

作者：
    @Wujee

创建日期：2026-10-13
版本：1.0.0

许可证：内部使用，未经许可不得传播。

"""

import os
import re
import io
import json
import base64
import urllib.request
import urllib.error

from utils.mlnlog import MLN_LOG_INFO, MLN_LOG_WARN, MLN_LOG_DEBUG, MLN_LOG_EXCEPTION

# OpenAI 兼容端点（多模态模型统一走这里）
_ENDPOINT = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"

# 默认模型：qwen3-omni-flash（全模态视觉对话，实测文本 ~1.3s，交互友好；
# 免费额度到期 2026-11-04）。qwen3.8-omni-flash 虽有效期更长但实测响应 50s+、
# 易超时，仅留作备选。qwen-mt-uni 是「多模态翻译」模型，要求 target_lang，
# 不能做视觉理解，切勿使用。可用环境变量 QWEN_MODEL 切换。
_DEFAULT_MODEL = "qwen3-omni-flash"
_FALLBACK_MODEL = "qwen3.5-omni-flash"

_TIMEOUT = 60

# 运行期熔断标志：额度耗尽/鉴权失败后置 True，本进程内不再重复请求
_quota_dead = False
_candidate_cache = None


# ==============================================================================
# 可用性
# ==============================================================================
def available() -> bool:
    """是否具备调用多模态的条件（有密钥且未熔断）。"""
    if _quota_dead:
        return False
    return bool(os.environ.get("DASHSCOPE_API_KEY", "").strip())


def _model_name() -> str:
    return os.environ.get("QWEN_MODEL", _DEFAULT_MODEL).strip() or _DEFAULT_MODEL


# ==============================================================================
# 注册表候选清单（约束模型输出到合法类别）
# ==============================================================================
def _candidates():
    """返回 [(class_key, display_name, category)]，带缓存。"""
    global _candidate_cache
    if _candidate_cache is not None:
        return _candidate_cache
    try:
        from service.registry import all_classes
        rows = all_classes(only_active=True)
        _candidate_cache = [
            (r["class_key"], r.get("display_name", ""), r.get("category", ""))
            for r in rows
        ]
    except Exception as e:
        MLN_LOG_EXCEPTION("多模态读取注册表失败：%s", e)
        _candidate_cache = []
    return _candidate_cache


def _candidate_text() -> str:
    lines = []
    for i, (key, disp, cat) in enumerate(_candidates()):
        lines.append(f"{i:02d}. {key}（{disp}，{cat}）")
    return "\n".join(lines)


def _resolve_key(raw: str) -> str:
    """模型返回的 key/名称 -> 注册表 class_key，匹配不上则原样返回。"""
    if not raw:
        return raw
    raw = raw.strip()
    cands = _candidates()
    keys = {k for k, _, _ in cands}
    if raw in keys:
        return raw

    # 1) 模型常照抄候选整行（如「02. tiao_7（挑七，single）」），
    #    直接在文本里按最长优先搜合法 key 子串
    low = raw.lower()
    for k in sorted(keys, key=len, reverse=True):
        if re.search(r"(?<![a-z0-9])" + re.escape(k) + r"(?![a-z0-9])", low):
            return k

    # 2) 中文名精确匹配
    disp = {d: k for k, d, _ in cands if d}
    if raw in disp:
        return disp[raw]

    # 3) 去符号/序号后整体相等
    norm = "".join(ch for ch in low if ch not in " _-－—·.，,。:：()（）0123456789")
    for k, d, _ in cands:
        if "".join(ch for ch in k.lower() if ch.isalnum()) == norm:
            return k
        if d and "".join(ch for ch in d.lower() if ch.isalnum()) == norm:
            return k
    return raw


# ==============================================================================
# HTTP 调用（标准库）
# ==============================================================================
def _chat(messages, model=None, timeout=None):
    """
    调用兼容端点。返回 (ok, content_text)。
    403/额度耗尽/鉴权失败会熔断；其它异常返回 (False, None)。
    timeout 秒，缺省 _TIMEOUT；图像类调用可传更长时间。
    """
    global _quota_dead
    api_key = os.environ.get("DASHSCOPE_API_KEY", "").strip()
    if not api_key:
        return False, None
    if _quota_dead:
        return False, None

    body = json.dumps({
        "model": model or _model_name(),
        "messages": messages,
        "temperature": 0.1,
    }, ensure_ascii=False).encode("utf-8")

    req = urllib.request.Request(
        _ENDPOINT,
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout or _TIMEOUT) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        content = data["choices"][0]["message"]["content"]
        return True, content
    except urllib.error.HTTPError as e:
        text = ""
        try:
            text = e.read().decode("utf-8", "ignore")
        except Exception:
            pass
        if e.code == 403 or "AllocationQuota.FreeTierOnly" in text or e.code in (401, 429):
            _quota_dead = True
            MLN_LOG_WARN("多模态额度/鉴权不可用（HTTP %s），已熔断，后续走假数据：%s",
                         e.code, text[:200])
        else:
            MLN_LOG_WARN("多模态请求失败 HTTP %s：%s", e.code, text[:200])
        return False, None
    except Exception as e:
        MLN_LOG_WARN("多模态调用异常（网络/超时），降级假数据：%s", e)
        return False, None


def _extract_json(text: str):
    """从模型回复中抠出 JSON（容忍 ```json 包裹与前后说明文字）。"""
    if not text:
        return None
    s = text.strip()
    if s.startswith("```"):
        s = s.strip("`")
        if s.lower().startswith("json"):
            s = s[4:]
    # 找第一个 { 到最后一个 }
    i, j = s.find("{"), s.rfind("}")
    if i != -1 and j != -1 and j > i:
        try:
            return json.loads(s[i:j + 1])
        except Exception:
            return None
    return None


# ==============================================================================
# 单字识别（多模态）
# ==============================================================================
def classify_crop(pil_img):
    """
    入参：单个减字裁剪图（PIL.Image）
    返回：
        成功 -> (True, [(class_key, confidence), ...])
        不可用/失败 -> (False, [])
    """
    if not available():
        return False, []

    try:
        # 压缩到长边 960、JPEG 质量 85，减小 base64 体积与多模态处理时延
        img = pil_img.convert("RGB")
        max_side = max(img.size)
        if max_side > 960:
            scale = 960.0 / max_side
            img = img.resize((max(1, int(img.size[0] * scale)),
                              max(1, int(img.size[1] * scale))))
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85)
        b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    except Exception as e:
        MLN_LOG_WARN("裁剪图编码失败，多模态降级：%s", e)
        return False, []

    prompt = (
        "你是古琴减字谱专家。图片中是一个古琴减字（可能是右手指法、左手按音、"
        "装饰音或复合减字）。请严格从下列候选类别中选出最匹配的一个，"
        "确有把握时最多再给 2 个候选，按置信度从高到低排列。\n"
        "候选类别（key（中文名，类别））：\n"
        f"{_candidate_text()}\n\n"
        "只返回 JSON，不要任何解释，格式：\n"
        '{"keys":[{"key":"class_key","confidence":0.95}]}'
    )

    messages = [{
        "role": "user",
        "content": [
            {"type": "image_url",
             "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
            {"type": "text", "text": prompt},
        ],
    }]

    ok, content = _chat(messages, timeout=90)
    if not ok:
        return False, []
    data = _extract_json(content)
    if not data or not isinstance(data.get("keys"), list) or not data["keys"]:
        MLN_LOG_WARN("多模态单字返回无法解析：%s", (content or "")[:200])
        return False, []

    result = []
    for it in data["keys"][:3]:
        if not isinstance(it, dict):
            continue
        key = _resolve_key(str(it.get("key", "")))
        try:
            conf = float(it.get("confidence", 0.5))
        except Exception:
            conf = 0.5
        conf = max(0.0, min(1.0, conf))
        if key and key not in [k for k, _ in result]:
            result.append((key, round(conf, 4)))
    if not result:
        return False, []
    MLN_LOG_INFO("多模态单字识别：%s", result)
    return True, result


# ==============================================================================
# 智能句读（纯文本，按古琴乐理标 C/S/L/E/U）
# ==============================================================================
def segment(chars):
    """
    入参：减字 class_key 列表
    返回：
        成功 -> (True, [label, ...])，label ∈ C/S/L/E/U
        失败 -> (False, [])
    """
    if not available():
        return False, []

    disp = {k: d for k, d, _ in _candidates()}
    numbered = "\n".join(
        f"{i:02d}. {k}（{disp.get(k, '未知')}）" for i, k in enumerate(chars)
    )

    prompt = (
        "你是古琴打谱专家。下面是一段按演奏顺序排列的减字（key（中文名））。\n"
        f"{numbered}\n\n"
        "请依据古琴乐理为每个字标注它与下一音之间的边界：\n"
        "C=连续（紧密相连的音）；S=短停（小乐逗/气口）；"
        "L=长停（乐句内较大停顿）；E=句末（一个完整乐句/段落结束）；"
        "U=无法判断（信息不足）。\n"
        "请综合考虑：句末多落在完整指法组合之后、散按交替、复音（撮）、"
        "以及左手走音（撞/吟猱等装饰音）通常与其后音相连。\n"
        "只返回 JSON，数量与输入一致且顺序不变：\n"
        '{"labels":[{"key":"...","label":"C","confidence":0.9}]}'
    )
    messages = [{"role": "user", "content": [{"type": "text", "text": prompt}]}]

    ok, content = _chat(messages)
    if not ok:
        return False, []
    data = _extract_json(content)
    if not data or not isinstance(data.get("labels"), list):
        MLN_LOG_WARN("多模态句读返回无法解析：%s", (content or "")[:200])
        return False, []

    labels = []
    valid = {"C", "S", "L", "E", "U"}
    for it in data["labels"]:
        if isinstance(it, dict):
            lab = str(it.get("label", "C")).upper()
            labels.append(lab if lab in valid else "C")
        else:
            labels.append("C")
    if len(labels) != len(chars):
        MLN_LOG_WARN("多模态句读返回数量不符（%d/%d），降级假规则",
                     len(labels), len(chars))
        return False, []
    MLN_LOG_INFO("多模态句读完成：%d 字", len(labels))
    return True, labels
