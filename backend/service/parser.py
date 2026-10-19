# -*- coding: utf-8 -*-
"""
减字解析模块：严格解析两种key格式，输出标准结构化dict
1. 散音：san_tiao_7（前缀san，散音挑七弦）
2. 按音：ming_10_gou_5（左手_徽位_右手指法_弦）
3. 纯右手：gou_5
"""
from service import registry
from utils.mlnlog import MLN_LOG_INFO

# 拼音-中文映射表
RH_MAP = {"tiao": "挑", "gou": "勾", "mo": "抹", "ti": "剔", "da": "打", "san": "散"}
LH_MAP = {"ming": "名指", "zhong": "中指", "da": "大指", "shi": "食指"}
STR_MAP = {"1": "一弦", "2": "二弦", "3": "三弦", "4": "四弦",
           "5": "五弦", "6": "六弦", "7": "七弦"}
HUI_MAP = {"10": "十", "9": "九", "8": "八", "7": "七", "6": "六", "5": "五", "4": "四", "12": "十二"}


def char_parse(raw_key: str) -> dict:
    raw_key = str(raw_key)
    parts = raw_key.split("_")

    rh_key = None
    string_key = None
    lh_key = None
    hui_key = None
    category = "其他"

    # 格式1：san_tiao_7 散音
    if parts[0] == "san":
        if len(parts) >= 3:
            rh_key = parts[1]
            string_key = parts[2]
        lh_key = None
        hui_key = None
        category = "散音"
    # 格式2：ming_10_gou_5 按音（左手_徽位_右手_弦）
    elif len(parts) >= 4:
        lh_key = parts[0]
        hui_key = parts[1]
        rh_key = parts[2]
        string_key = parts[3]
        category = "按音"
    # 格式3：gou_5 纯右手散音
    elif len(parts) == 2:
        rh_key = parts[0]
        string_key = parts[1]
        lh_key = None
        hui_key = None
        category = "散音"

    # 解析右手
    rh_cn = RH_MAP.get(rh_key, rh_key or "")
    str_cn = STR_MAP.get(string_key, string_key or "")
    rh_text = f"{rh_cn} · {str_cn}" if rh_cn and str_cn else "—"

    # 解析左手
    if category == "散音":
        lh_text = "散音（不按弦）"
    else:
        lh_cn = LH_MAP.get(lh_key, lh_key or "")
        hui_cn = HUI_MAP.get(hui_key, hui_key or "")
        lh_text = f"{lh_cn}{hui_cn}徽" if lh_cn and hui_cn else "—"

    # 生成描述
    if category == "散音":
        desc = f"右手{rh_cn}弹{str_cn}空弦，左手不按弦，散音演奏。"
    elif category == "按音":
        desc = f"右手{rh_cn}弹{str_cn}，左手{lh_text}按弦，按音演奏。"
    else:
        desc = f"{raw_key}，指法释义待补充。"

    display_name = rh_text.replace(" · ", "") if category == "散音" else lh_text + rh_text.replace(" · ", "")
    MLN_LOG_INFO("解析减字：%s → %s", raw_key, display_name)

    return {
        "raw_key": raw_key,
        "display_name": display_name,
        "category": category,
        "right_hand": {"text": rh_text, "finger": rh_cn, "string": str_cn},
        "left_hand": {"text": lh_text, "finger": LH_MAP.get(lh_key, ""), "hui": HUI_MAP.get(hui_key, "")},
        "desc": desc
    }
