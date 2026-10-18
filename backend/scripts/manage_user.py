# -*- coding: utf-8 -*-
"""
用户管理命令行工具

用法（先 cd backend）：
    python scripts/manage_user.py add <username> [--role admin|user]
    python scripts/manage_user.py list
    python scripts/manage_user.py reset <username>
    python scripts/manage_user.py disable <username>
    python scripts/manage_user.py enable <username>

密码通过 getpass 交互输入，不进命令行历史。

作者：
    @zlxaaa

创建日期：2026-10-18
版本：1.0.0
"""

import argparse
import getpass
import sys
from pathlib import Path

# 允许从 backend/ 目录直接运行
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core import db
from service import user_store


def _ask_password() -> str:
    p1 = getpass.getpass("输入密码（>=8位）：")
    if len(p1) < 8:
        print("密码至少 8 位"); sys.exit(1)
    p2 = getpass.getpass("再输入一次：")
    if p1 != p2:
        print("两次输入不一致"); sys.exit(1)
    return p1


def cmd_add(args):
    if user_store.get_user_raw(args.username):
        print(f"用户已存在：{args.username}"); return
    pwd = _ask_password()
    user_store.create_user(args.username, pwd, role=args.role)
    print(f"已创建 {args.username}（role={args.role}）")


def cmd_list(_args):
    users = user_store.list_users()
    if not users:
        print("（无用户）"); return
    print(f'{"id":<5}{"用户名":<16}{"角色":<8}{"状态":<6}创建时间')
    for u in users:
        status = "禁用" if u.get("disabled") else "正常"
        print(f'{u["id"]:<5}{u["username"]:<16}{u.get("role", "user"):<8}{status:<6}{u.get("created_at", "-")}')


def cmd_reset(args):
    u = user_store.get_user_raw(args.username)
    if not u:
        print("用户不存在"); return
    pwd = _ask_password()
    user_store.reset_password(u["id"], pwd)
    print("密码已重置")


def cmd_toggle(args, disabled: bool):
    u = user_store.get_user_raw(args.username)
    if not u:
        print("用户不存在"); return
    user_store.set_disabled(u["id"], disabled)
    print("已禁用" if disabled else "已启用")


def main():
    db.init_schema()

    p = argparse.ArgumentParser(description="泠弦智谱用户管理")
    sub = p.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("add"); a.add_argument("username")
    a.add_argument("--role", default="user", choices=["admin", "user"])
    a.set_defaults(func=cmd_add)

    l = sub.add_parser("list"); l.set_defaults(func=cmd_list)

    r = sub.add_parser("reset"); r.add_argument("username")
    r.set_defaults(func=cmd_reset)

    d = sub.add_parser("disable"); d.add_argument("username")
    d.set_defaults(func=lambda args: cmd_toggle(args, True))

    e = sub.add_parser("enable"); e.add_argument("username")
    e.set_defaults(func=lambda args: cmd_toggle(args, False))

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()