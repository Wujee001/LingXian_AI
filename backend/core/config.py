# -*- coding: utf-8 -*-
"""
全局配置模块

统一定义后端各目录的绝对路径，全部基于本文件位置拼接，
禁止写死盘符；启动时自动确保静态、上传、临时、模型、
日志、数据等目录存在。

作者：
    @Wujee

创建日期：2026-10-1
版本：1.0.0

许可证：内部使用，未经许可不得传播。

"""

import os

# 本文件位于 backend/core/config.py，逐级回溯到 backend 根目录
CORE_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_ROOT = os.path.dirname(CORE_DIR)

# 静态资源目录（main.py 将 /static 挂载到此）
STATIC_DIR = os.path.join(BACKEND_ROOT, "static")

# 整谱上传图保存位置：static/upload，可通过 /static/upload/xxx 访问
UPLOAD_DIR = os.path.join(STATIC_DIR, "upload")

# 临时裁剪/处理目录（不对外提供）
TEMP_DIR = os.path.join(BACKEND_ROOT, "temp_upload")

# 模型权重目录（.gitignore，走 GitHub Release）
MODEL_DIR = os.path.join(BACKEND_ROOT, "models")

# 日志输出目录（.gitignore）
LOG_DIR = os.path.join(BACKEND_ROOT, "logs")

# 后端业务数据目录（class_registry.csv、知识库）
DATA_DIR = os.path.join(BACKEND_ROOT, "data")

# 启动时确保全部目录存在
for _dir in (STATIC_DIR, UPLOAD_DIR, TEMP_DIR, MODEL_DIR, LOG_DIR, DATA_DIR):
    os.makedirs(_dir, exist_ok=True)