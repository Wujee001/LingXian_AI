# 泠弦智谱 LingXianAI

古琴减字谱智能识别与打谱系统（全球校园 AI 算法精英大赛 · 泠弦智谱团队）。

> **2026-10-18 `develop-x` 双模型联调修改**：本版本将 `backend/models/best.pt` 明确限定为**单类别减字定位权重**；`backend/models/stage2_best.pth` 用于 **ResNet18 八字段指法候选识别**，两者不能互换。预测不是专家确认，首次输出标为待复核。安装、接口变化和真实验收请先阅读 [双模型接入与人工复核说明](docs/双模型接入_人工复核与验收.md)。
>
> **2026-10-19 登录与内容模块（@zlxaaa）**：新增账号登录、用户管理、历史记录、个人笔记、广场。密码用 PBKDF2 加盐存储，token 内存态 12 小时有效。详见 [第七节 账号与权限](#七账号与权限zlxaaa)。

面向古琴学习者，提供**单减字识别、指法解析、整谱打谱、节奏（句读）划分**，以及**登录、历史、笔记、广场**等辅助功能。

- 前端：Vue3 + Element-Plus + Vite（国风宣纸主题），端口 `5173`
- 后端：FastAPI + Uvicorn，端口 `8001`
- 部署：本地单机演示，不上云，推理仅需 CPU
- 存储：SQLite（`backend/data/app.db`）+ 文件系统（历史快照图）

> 训练在 Google Colab（GPU）完成，产出权重后下载到本地 `backend/models/`；
> 项目运行（推理）在本地 CPU 即可，训练与推理解耦。

---

## 目录

- [一、目录结构](#一目录结构)
- [二、环境准备（首次）](#二环境准备首次)
- [三、首次启动：建管理员账号](#三首次启动建管理员账号)
- [四、启动（开两个终端）](#四启动开两个终端)
- [五、功能与接口](#五功能与接口)
- [六、接入真实权重（双模型版）](#六接入真实权重双模型版)
- [七、账号与权限（@zlxaaa）](#七账号与权限zlxaaa)
- [八、常见问题](#八常见问题)
- [九、维护与致谢](#九维护与致谢)

---

## 一、目录结构

```text
LingXian_AI/
├─ backend/
│  ├─ main.py                  # FastAPI 入口（CORS/静态/路由/启动钩子）
│  ├─ api/
│  │  ├─ single_char.py        # 单减字识别（含写历史）
│  │  ├─ whole_sheet.py        # 整谱打谱（含写历史）
│  │  ├─ knowledge.py          # 知识库
│  │  ├─ judou.py              # 智能句读
│  │  ├─ auth.py               # 登录 / 退出 / me
│  │  ├─ admin.py              # 用户管理 + 被隐藏内容 + 审计
│  │  ├─ history.py            # 我的历史
│  │  ├─ notes.py              # 我的笔记
│  │  └─ square.py             # 广场（公开笔记/历史 + 隐藏）
│  ├─ core/
│  │  ├─ config.py             # 路径与常量（DB_PATH / TOKEN_TTL / HISTORY_IMG_DIR）
│  │  ├─ auth.py               # PBKDF2 哈希 + token + require_user/require_admin/optional_user
│  │  ├─ db.py                 # SQLite 连接与建表
│  │  └─ jianzipu_lib.json     # 减字语义知识库（25 类）
│  ├─ service/
│  │  ├─ stage2_reader.py      # ResNet18 八字段推理
│  │  ├─ yolo_infer.py         # YOLO 单类别定位
│  │  ├─ qwen_adapter.py       # 多模态兜底
│  │  ├─ attribute_parser.py   # 属性格式化
│  │  ├─ parser.py             # 减字解析
│  │  ├─ registry.py           # 类别主表加载
│  │  ├─ correction_store.py   # 人工修正落库
│  │  ├─ user_store.py         # 用户表 CRUD
│  │  ├─ history_store.py      # 历史记录 CRUD
│  │  ├─ note_store.py         # 笔记 CRUD（nh3 sanitize）
│  │  ├─ audit_store.py        # 审计写入
│  │  └─ image_store.py        # 历史快照复制 + 缩略图
│  ├─ scripts/
│  │  └─ manage_user.py        # 命令行管账号（add/list/reset/disable/enable）
│  ├─ data/
│  │  ├─ class_registry.csv    # 类别主表（进 Git）
│  │  ├─ app.db                # SQLite（.gitignore）
│  │  └─ history_images/       # 历史快照图（.gitignore）
│  ├─ models/                  # 权重目录（.gitignore）
│  ├─ static/upload/           # 上传图（.gitignore）
│  ├─ temp_upload/             # 临时目录
│  ├─ logs/                    # 日志
│  ├─ utils/mlnlog.py          # 日志系统
│  └─ modules/                 # 智能句读算法（V2 预留）
├─ frontend/
│  ├─ src/
│  │  ├─ api/index.js          # axios 封装（含 401 拦截 + Bearer）
│  │  ├─ store/auth.js         # token + user 响应式状态
│  │  ├─ router/index.js       # 路由 + 守卫
│  │  ├─ views/
│  │  │  ├─ SingleChar.vue     # 单减字识别
│  │  │  ├─ WholeSheet.vue     # 整谱打谱
│  │  │  ├─ Knowledge.vue      # 减字库（含“记一笔”）
│  │  │  ├─ Judou.vue          # 智能句读
│  │  │  ├─ Login.vue          # 登录
│  │  │  ├─ History.vue        # 我的历史
│  │  │  ├─ Notes.vue          # 我的笔记
│  │  │  ├─ Square.vue         # 广场
│  │  │  └─ AdminUsers.vue     # 管理员工作台（用户/被隐藏内容/审计）
│  │  └─ components/
│  │     ├─ SheetCanvas.vue    # 谱图画布
│  │     ├─ NoteEditor.vue     # Markdown 编辑器（md-editor-v3）
│  │     └─ MarkdownView.vue   # 只读 Markdown
│  └─ package.json
├─ data/dataset/               # 训练数据集（网盘，不进 Git）
├─ scripts/                    # Colab 训练 Notebook
└─ docs/                       # 架构、接口契约、句读规则手册
```

---

## 二、环境准备（首次）

```powershell
# 后端虚拟环境
conda create -n lingxian python=3.10 -y
conda activate lingxian

# 后端依赖（含 nh3，用于 Markdown sanitize）
python -m pip install -r requirements.txt
python -m pip install nh3

# YOLO 推理依赖（可选，不装会自动降级）
python -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
python -m pip install ultralytics

# 前端依赖（含 md-editor-v3）
cd frontend
npm config set registry https://registry.npmmirror.com
npm install
```

**依赖清单增量**（相对 V1）：

| 侧 | 包 | 用途 |
|---|---|---|
| Python | `nh3` | 笔记 Markdown 的 HTML sanitize |
| npm | `md-editor-v3`（>=6.5.4，实测 7.1.0） | Markdown 编辑器 |

---

## 三、首次启动：建管理员账号

数据库首次启动会自动建表，但**不会自动建账号**（除设置环境变量外）。先建管理员：

```powershell
conda activate lingxian
cd backend
python scripts/manage_user.py add admin --role admin
```

按提示交互输入密码（≥8 位），密码不进命令行历史。

> **可选**：设环境变量 `LINGXIAN_ADMIN_PASSWORD` 后首次启动会自动建 admin，密码取环境变量；不设则随机生成并打印在日志里。已有 admin 时该变量不生效。
>
> ```powershell
> # 仅当前 PowerShell 窗口生效
> $env:LINGXIAN_ADMIN_PASSWORD = "你的强密码"
>
> # 当前用户永久生效（需重开终端）
> [Environment]::SetEnvironmentVariable("LINGXIAN_ADMIN_PASSWORD", "你的强密码", "User")
> ```

日常增删账号一律用 `manage_user.py`（不需要登录、不经过网络）：

```powershell
python scripts/manage_user.py list                    # 列出
python scripts/manage_user.py add alice               # 加普通用户
python scripts/manage_user.py add admin2 --role admin # 加第二个管理员
python scripts/manage_user.py reset admin             # 重置密码
python scripts/manage_user.py disable alice           # 禁用（不删，保留历史归属）
python scripts/manage_user.py enable alice            # 启用
```

> 忘记管理员密码时，用 `manage_user.py reset <用户名>` 即可，**不需要删库、不需要重启后端**。

---

## 四、启动（开两个终端）

**终端 1 — 后端：**

```powershell
conda activate lingxian
cd backend
python main.py
```

看到 `Uvicorn running on http://127.0.0.1:8001` 即成功。

接口文档：<http://127.0.0.1:8001/docs>

**终端 2 — 前端：**

```powershell
cd frontend
npm run dev
```

浏览器打开 <http://127.0.0.1:5173>。

> 前端已配置 `/api`、`/static`、`/history_images` 代理到 `8001`，无需处理跨域。
>
> **双模型版不再自动生成演示数据**：后端或权重未就绪时页面会明确提醒，可手动添加/修正框；正式比赛展示必须核实两个模型状态，避免误把旧演示数据当作模型能力。

---

## 五、功能与接口

### 5.1 识别类（公开，未登录可用）

| 功能 | 接口 | 说明 |
| --- | --- | --- |
| 单减字识别 | `POST /api/char/predict` | 上传单字图，返回 Top-3 候选 + 指法解析。**登录用户识别成功后自动写历史** |
| 整谱打谱 | `POST /api/sheet/upload` | 上传整页谱，返回检测框、逐框候选与解析。**登录用户自动写历史快照** |
| 人工修正 | `POST /api/sheet/correct` | 记录人工修正 |
| 知识库 | `GET /api/knowledge/library`、`/detail/{key}`、`/search`、`/registry` | 减字语义查询 |
| 智能句读 | `POST /api/judou/segment` | 输入 class_key 序列，输出 C/S/L/E/U |

### 5.2 认证与用户（需登录 / 管理员）

| 功能 | 接口 | 权限 |
| --- | --- | --- |
| 登录 | `POST /api/auth/login` | 公开 |
| 退出 | `POST /api/auth/logout` | 需登录 |
| 当前用户 | `GET /api/auth/me` | 需登录 |
| 用户列表 | `GET /api/admin/users` | 管理员 |
| 添加用户 | `POST /api/admin/users` | 管理员 |
| 禁用/启用 | `PATCH /api/admin/users/{id}` | 管理员 |
| 重置密码 | `POST /api/admin/users/{id}/reset-password` | 管理员 |
| 审计列表 | `GET /api/admin/audit` | 管理员 |
| 被隐藏笔记 | `GET /api/admin/hidden/notes` | 管理员 |
| 被隐藏历史 | `GET /api/admin/hidden/history` | 管理员 |
| 解除隐藏 | `PATCH /api/admin/hidden/{notes\|history}/{id}/unhide` | 管理员 |

### 5.3 历史 / 笔记 / 广场（需登录）

| 功能 | 接口 |
| --- | --- |
| 我的历史 | `GET /api/history`、`DELETE /api/history/{id}`、`PATCH /api/history/{id}/visibility` |
| 我的笔记 | `GET/POST /api/notes`、`PUT/DELETE /api/notes/{id}`、`PATCH /api/notes/{id}/visibility` |
| 广场公开笔记 | `GET /api/square/notes`、`GET /api/square/notes/{id}` |
| 广场公开历史 | `GET /api/square/history`、`GET /api/square/history/{id}` |
| 管理员隐藏 | `PATCH /api/square/{notes\|history}/{id}/hide` |

---

## 六、接入真实权重（双模型版）

模型线需同时交付：

1. `backend/models/best.pt`：**单类别减字区域检测** YOLO11n（类名须为 `jianzi`）
2. `backend/models/stage2_best.pth`：八字段 ResNet18 多任务分类权重，内含 vocab
3. 相应的独立测试结果和训练版本信息

安装后端推理依赖后重启：

```powershell
python -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
python -m pip install -r requirements.txt
cd backend
python main.py
```

`GET /api/sheet/model-status` 应显示两个 `available: true`。默认只产生**待人工复核的指法属性候选**；旧 25 类知识库仍可通过手动 `class_key` 检索，但模型不会凭单类别检测 id 猜完整指法。具体步骤见 [双模型接入与验收](docs/双模型接入_人工复核与验收.md)。

**权重不进 Git**：单独放置或由模型线发布，不随源码上传。

---

## 七、账号与权限（@zlxaaa）

### 7.1 认证方式

- **密码**：PBKDF2-HMAC-SHA256，每用户独立 16 字节随机盐，迭代 200,000 次，`hashlib.pbkdf2_hmac` 标准库实现，零新增认证依赖
- **比较**：`hmac.compare_digest` 常数时间，防时序攻击
- **token**：`secrets.token_urlsafe(32)` 随机串，内存字典保存，**重启后端即失效**（本地单机特性，非缺陷）
- **有效期**：12 小时（`config.py` 的 `TOKEN_TTL_HOURS`）
- **传输**：`Authorization: Bearer <token>`，前端存 `localStorage`

### 7.2 权限矩阵

| 操作 | 未登录 | 普通用户 | 管理员 |
|---|---|---|---|
| 单字 / 整谱 / 知识库 / 句读 | ✅ | ✅ | ✅ |
| 写历史 | ❌ | ✅ | ✅ |
| 我的历史 / 我的笔记 / 广场 | ❌ | ✅ | ✅ |
| 公开自己的内容 | ❌ | ✅ | ✅ |
| 被管理员隐藏后自行重开 | — | ❌ | ❌ |
| 用户管理（增/禁用/重置） | ❌ | ❌ | ✅ |
| 查看 / 解除隐藏 | ❌ | ❌ | ✅ |
| 审计日志 | ❌ | ❌ | ✅ |

### 7.3 可见性状态机

```text
private ──用户公开──→ public ──管理员隐藏──→ admin_hidden
   ↑                                              │
   └────────── 管理员解除隐藏 ─────────────────────┘
```

- `private ↔ public`：用户自主切换
- `public → admin_hidden`：管理员在广场点“隐藏”
- `admin_hidden → private`：管理员在「用户管理 → 被隐藏内容」点“解除隐藏”
- `admin_hidden → public`：**任何角色都不允许直接跳**，用户需先被解除隐藏，再自行公开

### 7.4 审计动作

`add_user` / `disable_user` / `enable_user` / `reset_password` / `hide_content` / `unhide_content`。不记录密码和 token。

---

## 八、常见问题

### 8.1 启动与依赖

- **端口被占用**：后端改 `uvicorn main:app --reload --port 8002`，同步改 `frontend/vite.config.js` 代理目标。
- **npm install 卡住**：确认已设淘宝镜像 `npm config get registry`。
- **ModuleNotFoundError**：确认已 `conda activate lingxian` 且在项目根执行过 `pip install -r requirements.txt`。
- **`ModuleNotFoundError: No module named 'nh3'`**：`python -m pip install nh3`，确认在 `(lingxian)` 环境里执行。
- **`ValueError: "rel" attribute is not allowed for tag "a" when link_rel is set`**：`note_store.py` 的 `ALLOWED_ATTRS` 里 `"a"` 不能含 `"rel"`（nh3 自动加），删掉即可。
- **`md-editor-v3` import 报错**：7.x 用 `import { MdEditor } from 'md-editor-v3'`（具名导出），4.x 是默认导出，按装到的版本调整。

### 8.2 账号

- **忘记管理员密码**：`python scripts/manage_user.py reset <用户名>`，不需要删库、不需要重启。
- **管理员被禁用了**：`python scripts/manage_user.py enable admin` 先启用，再 `reset`。
- **所有 admin 都丢了**：`manage_user.py` 直接读写 SQLite，不经过登录，永远可用；实在不行 `python scripts/manage_user.py add admin3 --role admin`。
- **想换台机器但保留账号**：备份 `backend/data/app.db` + `backend/data/history_images/`（两者是一对，缺一不可）。

### 8.3 模型与识别

- **后端没有模型候选**：检查 `/api/sheet/model-status` 和两个权重是否放对路径，不再把演示输出当成真实结果。
- **整谱未出框**：规则检测对图片质量敏感，换背景干净、字块清晰、无大段批注的谱图。
- **中文路径报错**：项目路径保持纯英文，勿放在含中文的父目录下。

### 8.4 内容与安全

- **笔记里的 `<script>` 消失**：正常。后端 `nh3` 白名单 sanitize，保留 `<b> <i> <a> <code> <pre> <table>` 等安全标签，移除 `<script> <iframe>` 和 `on*` 事件、`javascript:` 协议。
- **历史图片访问**：`/history_images/{user_id}/{uuid}.png`，UUID 不可猜，本地单机场景可接受。
- **`.env` / `app.db` 不要提交**：`.gitignore` 已覆盖，`git status --short` 确认。

---

## 九、维护与致谢

- 原 V1 双模型版：@Wujee 及模型线
- 登录、用户管理、历史、笔记、广场、审计：@zlxaaa（2026-10-19）
- 许可证：内部使用，未经许可不得传播