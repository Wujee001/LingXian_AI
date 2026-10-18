# -*- coding: utf-8 -*-
"""
SQLite 连接与初始化

线程本地连接 + WAL 模式 + 外键约束。每张表使用 IF NOT EXISTS，
重复启动幂等。图片不入库，只存文件系统相对路径。

作者：
    @zlxaaa

创建日期：2026-10-18
版本：1.0.0

许可证：内部使用，未经许可不得传播。
"""

import sqlite3
import threading

from core.config import DB_PATH
from utils.mlnlog import MLN_LOG_INFO, MLN_LOG_EXCEPTION

_local = threading.local()


_DDL = """
CREATE TABLE IF NOT EXISTS users (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  username    TEXT NOT NULL UNIQUE,
  algo        TEXT NOT NULL DEFAULT 'sha256',
  iterations  INTEGER NOT NULL DEFAULT 200000,
  salt        TEXT NOT NULL,
  pwd_hash    TEXT NOT NULL,
  role        TEXT NOT NULL DEFAULT 'user' CHECK(role IN ('admin','user')),
  disabled    INTEGER NOT NULL DEFAULT 0,
  created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS history (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id     INTEGER NOT NULL REFERENCES users(id),
  query_type  TEXT NOT NULL CHECK(query_type IN ('single','sheet','kb')),
  query_key   TEXT,
  parse_json  TEXT NOT NULL,
  image_path  TEXT,
  thumb_path  TEXT,
  visibility  TEXT NOT NULL DEFAULT 'private'
              CHECK(visibility IN ('private','public','admin_hidden')),
  created_at  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_history_user ON history(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_history_pub  ON history(visibility, created_at DESC);

CREATE TABLE IF NOT EXISTS notes (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id     INTEGER NOT NULL REFERENCES users(id),
  title       TEXT,
  content_md  TEXT NOT NULL,
  class_key   TEXT,
  visibility  TEXT NOT NULL DEFAULT 'private'
              CHECK(visibility IN ('private','public','admin_hidden')),
  created_at  TEXT NOT NULL,
  updated_at  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_notes_user ON notes(user_id, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_notes_pub  ON notes(visibility, updated_at DESC);

CREATE TABLE IF NOT EXISTS admin_audit (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  admin_id     INTEGER NOT NULL REFERENCES users(id),
  action       TEXT NOT NULL,
  target_user  INTEGER,
  target_type  TEXT,
  target_id    INTEGER,
  detail_json  TEXT,
  created_at   TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_audit_time ON admin_audit(created_at DESC);
"""


def get_conn() -> sqlite3.Connection:
    """每个线程一个独立连接；行以 Row 对象返回，支持按列名取值。"""
    conn = getattr(_local, "conn", None)
    if conn is None:
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        _local.conn = conn
    return conn


def init_schema() -> None:
    """启动时调用；幂等。"""
    try:
        conn = get_conn()
        conn.executescript(_DDL)
        MLN_LOG_INFO("SQLite 表结构就绪：%s", DB_PATH)
    except Exception as e:
        MLN_LOG_EXCEPTION("SQLite 初始化失败：%s", e)
        raise