# -*- coding: utf-8 -*-
"""
FastAPI 后端入口模块

创建应用实例、配置 CORS、挂载静态资源、注册全部路由。
V1 先启用整谱打谱路由，其余路由随模块就绪放开注释。

作者：
    @Wujee

创建日期：2026-10-1
版本：1.0.0

许可证：内部使用，未经许可不得传播。

"""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from utils.mlnlog import MlnLog, LogLevel
from core.config import STATIC_DIR, LOG_DIR
from api import whole_sheet, single_char, knowledge, judou

app = FastAPI(title="LingXianAI 泠弦智谱", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局开启文件日志
log_ins = MlnLog.initialize(level=LogLevel.DEBUG, console=True)
log_ins.set_log_file(os.path.join(LOG_DIR, "mlnlog.log"))

# 静态资源（上传的整谱图）
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# 路由注册
app.include_router(whole_sheet.router, prefix="/api/sheet", tags=["整谱打谱"])
app.include_router(single_char.router, prefix="/api/char", tags=["单字识别"])
app.include_router(knowledge.router, prefix="/api/knowledge", tags=["知识库"])
app.include_router(judou.router, prefix="/api/judou", tags=["智能句读"])


@app.get("/")
async def health():
    return {"code": 0, "msg": "LingXianAI backend ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8001, reload=True)