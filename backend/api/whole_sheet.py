# -*- coding: utf-8 -*-
"""
整谱打谱接口模块（泠弦智谱 V1）

整谱闭环，三级识别降级：
    1. 本地 YOLO 权重（service/yolo_infer.py）一次推理同时给出
       检测框 + 类别 + 置信度（主路线，离线）；
    2. YOLO 不可用时，先用 OpenCV 规则（detector）给位置框，
       再逐框裁剪交给 classifier（内部 YOLO→多模态→假数据）；
    3. 低置信度标 U 待人工复核。

人工修正 /correct 真正持久化到 data/corrections.json，
供模型线迭代训练。

上传仅允许 PNG/JPG/JPEG，文件名统一重命名（UUID），
规避中文路径与文件名冲突问题。

作者：
    @Wujee

更新日期：2026-10-13
版本：2.0.0

许可证：内部使用，未经许可不得传播。

"""

import os
import uuid

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from pydantic import BaseModel
from PIL import Image

from core.config import UPLOAD_DIR
from service.detector import detect
from service.classifier import predict_crop, get_last_source
from service.parser import char_parse
from service import correction_store
from utils.mlnlog import MLN_LOG_INFO, MLN_LOG_EXCEPTION, MLN_LOG_WARN

router = APIRouter()

# 低于该置信度的框标记为 U 人工复核
CONFIDENCE_TAU = 0.6

# 允许上传的图片格式（PNG + JPG/JPEG）
ALLOWED_EXT = {".png", ".jpg", ".jpeg"}


class SheetResp(BaseModel):
    success: bool
    data: dict


@router.post("/upload", response_model=SheetResp)
async def sheet_upload(file: UploadFile = File(...),
                       engine: str = Form("auto")):
    """上传整谱，返回检测框、逐框识别与解析结果。

    engine：auto 自动 / yolo 本地模型 / qwen 多模态（前端手动切换）。
    模型当前训练样本不足、分类不准，qwen 模式采用「YOLO 出框 +
    逐框多模态认字」，框位置仍由本地模型提供，分类交给多模态。
    """
    # 扩展名白名单 + 统一重命名（兼容 PNG/JPG/JPEG 与中文原文件名）
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXT:
        MLN_LOG_WARN("整谱上传被拒（非 PNG/JPG 图片）：%s", file.filename)
        raise HTTPException(status_code=400,
                            detail="仅支持 PNG / JPG / JPEG 格式图片")
    save_name = f"{uuid.uuid4().hex}{ext}"
    save_path = os.path.join(UPLOAD_DIR, save_name)

    content = await file.read()
    with open(save_path, "wb") as f:
        f.write(content)

    MLN_LOG_INFO("整谱上传：原名=%s 保存=%s（%d 字节）",
                 file.filename, save_name, len(content))

    # 校验图片可被 PIL 正常打开
    try:
        sheet_img = Image.open(save_path)
        sheet_img.load()
    except Exception as e:
        MLN_LOG_EXCEPTION("整谱图无法解析：%s", e)
        raise HTTPException(status_code=400, detail="图片文件已损坏或格式不支持")

    items, source = _recognize(save_path, sheet_img, engine)

    return {
        "success": True,
        "data": {
            "image_url": f"/static/upload/{save_name}",
            "source": source,
            "engine": engine,
            "items": items,
        },
    }


def _build_item(index: int, box: dict, candidates: list, raw_label):
    """统一组装单个框的返回结构；无候选时置空并标 U 待复核。"""
    if candidates:
        top_key, top_conf = candidates[0]
        return {
            "index": index,
            "box": box,
            "candidates": [[k, c] for k, c in candidates],
            "parse_result": char_parse(top_key),
            "status": "U" if top_conf < CONFIDENCE_TAU else "A",
            "raw_label": raw_label,
        }
    # 本地模型细类标签无法对应注册表（多模态未启用/失败）：交人工复核
    return {
        "index": index,
        "box": box,
        "candidates": [],
        "parse_result": None,
        "status": "U",
        "raw_label": raw_label,
    }


def _recognize(save_path: str, sheet_img: Image.Image, engine: str = "auto"):
    """
    整谱识别，返回 (items, source)。

    出框一律优先用本地 YOLO（检测框当前可用）；分类按 engine 分流：
        qwen：YOLO 出框 + 逐框裁剪多模态认字（当前最准，耗额度）；
        yolo：仅用 YOLO 自带分类，细类对不上基础 key 的框置空标 U；
        auto：YOLO 能对应基础 key 的框直接用，其余框补多模态认字。
    YOLO 完全不可用时，退 OpenCV 规则出框，逐框按所选引擎分类。
    """
    engine = (engine or "auto").strip().lower()
    if engine not in ("auto", "yolo", "qwen"):
        engine = "auto"

    # 第一级：本地 YOLO 出框（qwen 模式只取其框，分类重做多模态）
    yolo_items = []
    try:
        from service import yolo_infer
        ok, yitems, _ = yolo_infer.recognize(save_path)
        if ok and yitems:
            yolo_items = yitems
    except Exception as e:
        MLN_LOG_EXCEPTION("整谱 YOLO 出框异常，降级规则出框：%s", e)

    items = []
    used = set()

    if yolo_items:
        for i, d in enumerate(yolo_items):
            box = d["box"]
            key, conf = d.get("class_key"), d.get("confidence", 0.0)
            cands = []
            if engine == "qwen":
                cands = _crop_and_predict(sheet_img, box, "qwen")
                used.add(get_last_source())
            elif engine == "yolo":
                if key:
                    cands = [[key, conf]]
                used.add("yolo")
            else:  # auto：能对上基础 key 用本地，对不上补多模态
                if key:
                    cands = [[key, conf]]
                    used.add("yolo")
                else:
                    cands = _crop_and_predict(sheet_img, box, "qwen")
                    used.add(get_last_source())
            items.append(_build_item(i, box, cands, d.get("raw_label")))
        MLN_LOG_INFO("整谱走 YOLO 出框（引擎=%s），共 %d 框", engine, len(items))
    else:
        # 第二级：OpenCV 规则出框 + 逐框按引擎分类
        boxes = detect(save_path)
        for i, box in enumerate(boxes):
            try:
                cands = _crop_and_predict(sheet_img, box, engine)
                used.add(get_last_source())
                items.append(_build_item(i, box, cands, None))
            except Exception as e:
                MLN_LOG_EXCEPTION("第%d框处理异常：%s", i, e)
                items.append(_build_item(i, box, [], None))
        MLN_LOG_INFO("整谱走规则出框（引擎=%s），共 %d 框", engine, len(items))

    # 全局来源：只要有框走多模态即标 qwen，其次 yolo，最后 fake
    if "qwen" in used:
        source = "qwen"
    elif "yolo" in used:
        source = "yolo"
    else:
        source = "fake" if "fake" in used else "qwen"
    return items, source


@router.post("/correct")
async def sheet_correct(payload: dict):
    """
    人工修正回流（真正落库）。

    入参：
        image_url：谱图地址（可选）
        index：框序号
        box：调整后的框（可空）
        origin_key：模型原识别 key（可选）
        confirmed_key：人工确认的类别 key
        source：来源路线 yolo/qwen/fake（可选）
    """
    total = correction_store.append(payload)
    MLN_LOG_INFO(
        "人工修正回流：index=%s %s -> %s",
        payload.get("index"),
        payload.get("origin_key"),
        payload.get("confirmed_key"),
    )
    return {"success": True, "data": {"msg": "修正已记录", "total": total}}


def _crop_and_predict(sheet_img: Image.Image, box: dict, engine: str = "auto") -> list:
    """按归一化框裁剪，调用分类器（可指定引擎），返回 [(key, conf), ...]。"""
    w, h = sheet_img.size
    crop = sheet_img.crop((
        int(box["x"] * w),
        int(box["y"] * h),
        int((box["x"] + box["w"]) * w),
        int((box["y"] + box["h"]) * h),
    ))
    return predict_crop(crop, engine)
