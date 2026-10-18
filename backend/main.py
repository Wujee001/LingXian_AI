# -*- coding: utf-8 -*-
"""
FastAPI 后端入口模块

创建应用实例、配置 CORS、挂载静态资源、注册全部路由。
启动时初始化 SQLite 并预置 admin 账号。

作者：
    @Wujee
    @zlxaaa

创建日期：2026-10-1
版本：1.1.0（阶段 0：接入登录）

许可证：内部使用，未经许可不得传播。
"""

import os
import secrets
from api import (whole_sheet, single_char, knowledge, judou,
                 auth as auth_api, admin as admin_api, history as history_api,
                 notes as notes_api, square as square_api)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from utils.mlnlog import MlnLog, LogLevel, MLN_LOG_INFO, MLN_LOG_WARN, MLN_LOG_EXCEPTION
from core.config import STATIC_DIR, LOG_DIR, HISTORY_IMG_DIR
from core import db
from service.user_store import ensure_seed_admin
from api import whole_sheet, single_char, knowledge, judou, auth as auth_api, admin as admin_api, history as history_api
app = FastAPI(title="LingXianAI 泠弦智谱", version="1.1.0")

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
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/history_images", StaticFiles(directory=HISTORY_IMG_DIR), name="history_images")

@app.on_event("startup")
def _on_startup():
    db.init_schema()
    _seed_admin()


def _seed_admin():
    """预置 admin 账号；已存在则不覆盖。密码来源优先级：环境变量 > 临时生成。"""
    pwd = os.getenv("LINGXIAN_ADMIN_PASSWORD")
    temporary = False
    if not pwd:
        pwd = secrets.token_urlsafe(12)
        temporary = True
    try:
        created = ensure_seed_admin("admin", pwd)
    except Exception as e:
        MLN_LOG_EXCEPTION("预置 admin 失败：%s", e)
        return
    if not created:
        MLN_LOG_INFO("admin 已存在，跳过预置")
        return
    if temporary:
        MLN_LOG_WARN(
            "已预置管理员 admin，临时密码：%s —— 请登录后立刻重置，"
            "或下次启动前设置环境变量 LINGXIAN_ADMIN_PASSWORD", pwd
        )
    else:
        MLN_LOG_INFO("已预置管理员 admin（密码来自环境变量）")


# 路由注册
app.include_router(auth_api.router, prefix="/api/auth", tags=["认证"])
app.include_router(whole_sheet.router, prefix="/api/sheet", tags=["整谱打谱"])
app.include_router(single_char.router, prefix="/api/char", tags=["单字识别"])
app.include_router(knowledge.router, prefix="/api/knowledge", tags=["知识库"])
app.include_router(judou.router, prefix="/api/judou", tags=["智能句读"])
app.include_router(auth_api.router, prefix="/api/auth", tags=["认证"])
app.include_router(admin_api.router, prefix="/api/admin", tags=["用户管理"])   # ← 新增这行
app.include_router(whole_sheet.router, prefix="/api/sheet", tags=["整谱打谱"])
app.include_router(history_api.router, prefix="/api/history", tags=["历史记录"])
app.include_router(notes_api.router, prefix="/api/notes", tags=["个人笔记"])
app.include_router(square_api.router, prefix="/api/square", tags=["广场"])


@app.get("/")
async def health():
    return {"code": 0, "msg": "LingXianAI backend ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8001, reload=True)