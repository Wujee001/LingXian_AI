# 泠弦智谱 LingXianAI

古琴减字谱智能识别与打谱系统，面向古琴学习者，提供**单减字识别、指法解析、整谱打谱、节奏（句读）划分**。

- 前端：Vue3 + Element-Plus + Vite（国风宣纸主题），端口 `5173`
- 后端：FastAPI + Uvicorn，端口 `8001`
- 架构：**纯本地两阶段推理，无外网云 API 依赖**，CPU 即可运行

> 训练在 GPU 环境完成，产出权重后转存到本地 `backend/models/`，训练与推理解耦。

---

## 一、两阶段推理架构

| 阶段 | 权重 | 职责 |
|---|---|---|
| Stage1 | `best.pt` | YOLO 检测减字位置框，按竖排右起排序（模型仅 1 类，不分类） |
| Stage2 | `stage2_best.pth` | 多头 ResNet18 输出 8 个属性头（指法/弦/徽/修饰音），取前 5 拼 key |

识别 key 经 `parser` 归一化后查 `jianzipu_lib.json`（178 条）得到中文指法释义。
模型未就绪或权重缺失时接口直接返回 503/500，不返回假数据、不调用云 API。

---

## 二、目录结构

```
LingXian_AI_V1.0/
├─ backend/
│  ├─ main.py                  # FastAPI 入口（CORS/静态/日志/4 路由/预加载 Stage2）
│  ├─ api/                     # 路由层：single_char / whole_sheet / knowledge / judou
│  ├─ core/
│  │  ├─ config.py             # 全局路径（相对定位，禁写死盘符）
│  │  └─ jianzipu_lib.json     # 减字语义知识库（178 条）
│  ├─ service/
│  │  ├─ yolo_infer.py         # Stage1 YOLO 推理
│  │  ├─ stage2_infer.py       # Stage2 多头 ResNet18 推理
│  │  ├─ detector.py           # OpenCV 规则检测（备用出框）
│  │  ├─ parser.py             # key 归一化 + 查库释义
│  │  ├─ registry.py           # 类别主表加载（带缓存）
│  │  └─ correction_store.py   # 人工修正落库
│  ├─ data/class_registry.csv  # 类别主表（178 类）
│  ├─ models/                  # 权重目录（不进 Git，转存更新）
│  ├─ utils/
│  │  ├─ mlnlog.py             # 日志系统
│  │  └─ logs/                 # 统一日志/反馈目录
│  └─ modules/                 # 句读算法（V2 实现，当前空壳）
├─ frontend/
│  └─ src/
│     ├─ api/index.js          # 接口封装
│     ├─ views/                # SingleChar / WholeSheet / Knowledge / Judou
│     └─ components/SheetCanvas.vue
├─ scripts/                    # 训练 Notebook
└─ docs/                       # 架构、接口契约、句读规则、规划
```

---

## 三、环境准备

```powershell
# 1. 虚拟环境
conda create -n lingxian python=3.10 -y
conda activate lingxian

# 2. 后端依赖
pip install -r requirements.txt
# CPU 版 PyTorch（避免拉取 CUDA 大包），再装 ultralytics
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
pip install ultralytics

# 3. 前端依赖
cd frontend
npm config set registry https://registry.npmmirror.com   # 国内加速，仅一次
npm install
```

---

## 四、启动（两个终端）

**终端 1 — 后端：**

```powershell
conda activate lingxian
cd backend
python main.py
# 看到 Application startup complete 即成功
```

**终端 2 — 前端：**

```powershell
cd frontend
npm run dev
# 浏览器打开 http://127.0.0.1:5173
```

---

## 五、功能与接口

| 功能 | 接口 | 说明 |
|---|---|---|
| 单减字识别 | `POST /api/char/predict` | 上传单字图，返回候选与中文指法释义 |
| 整谱打谱 | `POST /api/sheet/upload` | 上传整谱，返回检测框与逐框识别结果 |
| 人工修正 | `POST /api/sheet/correct` | 手动修正，写入 feedback.txt 并落库 |
| 减字知识库 | `GET /api/knowledge/library`、`/detail/{key}`、`/search`、`/registry` | 浏览/筛选/检索 |
| 智能句读 | `POST /api/judou/segment` | V1 本地规则引擎，输出 C/S/L/E/U |

API 在线文档：http://127.0.0.1:8001/docs

---

## 六、权重说明（转存更新，不走 GitHub Release）

需放入 `backend/models/` 两个权重，均不进 Git：

1. `best.pt` —— Stage1 YOLO 检测权重，仅出减字位置框；
2. `stage2_best.pth` —— Stage2 多头 ResNet18 识别权重，输出指法/弦/徽属性。

权重通过**网盘 / U盘 / 本地拷贝**等方式在团队间转存更新，放入对应目录即可被自动加载，无需改代码。

---

## 七、日志与反馈

统一输出到 `backend/utils/logs/`：

- `mlnlog.log` —— 运行日志（`*.log` 不进 Git）。文件为 UTF-8，PowerShell 查看请用
  `Get-Content -Encoding UTF8`，直接 `Get-Content` 可能因默认编码显示中文乱码；
- `feedback.txt` —— 人工修正反馈，保留 Git 跟踪；
- 提交人工修正时，`correction_store` 还会在 `backend/data/` 生成 `corrections.json`。

---

## 八、常见问题

- **端口占用**：后端启动加 `--port 8002`，同步改 `vite.config.js` 代理目标。
- **识别服务不可用**：检查两个权重是否放入 `backend/models/`、ultralytics 是否装好。
- **日志中文乱码**：加 `-Encoding UTF8` 读取，文件本身正常。
- **npm install 卡住**：确认已设淘宝镜像 `npm config get registry`。
- **路径问题**：项目路径保持纯英文，避免中文路径导致图像处理失败。
