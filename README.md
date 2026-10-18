# 泠弦智谱 LingXianAI

古琴减字谱智能识别与打谱系统（全球校园 AI 算法精英大赛 · 泠弦智谱团队）。

> **2026-10-18 `develop-x` 双模型联调修改**：本版本将 `backend/models/best.pt` 明确限定为**单类别减字定位权重**；`backend/models/stage2_best.pth` 用于 **ResNet18 八字段指法候选识别**，两者不能互换。预测不是专家确认，首次输出标为待复核。安装、接口变化和真实验收请先阅读 [双模型接入与人工复核说明](docs/双模型接入_人工复核与验收.md)。下文部分描述保留原团队 V1 背景，不代表当前双模型接口语义。


面向古琴学习者，提供**单减字识别、指法解析、整谱打谱、节奏（句读）划分**。

- 前端：Vue3 + Element-Plus + Vite（国风宣纸主题），端口 `5173`
- 后端：FastAPI + Uvicorn，端口 `8001`
- 部署：本地单机演示，不上云，推理仅需 CPU

> 训练在 Google Colab（GPU）完成，产出权重后下载到本地 `backend/models/`；
> 项目运行（推理）在本地 CPU 即可，训练与推理解耦。

---

## 一、目录结构

```
LingXian_AI_V1.0/
├─ backend/
│  ├─ main.py                  # FastAPI 入口（挂载路由/CORS/静态资源/全局日志）
│  ├─ api/                     # 路由层：single_char / whole_sheet / knowledge / judou
│  ├─ core/
│  │  ├─ config.py             # 全局路径配置
│  │  └─ jianzipu_lib.json     # 减字语义知识库（25 类）
│  ├─ service/
│  │  ├─ classifier.py         # 单字分类（真权重优先，失败回退假模型）
│  │  ├─ detector.py           # 整谱减字框规则检测（OpenCV，V1 保留）
│  │  ├─ parser.py             # 识别结果 → 查知识库解析
│  │  └─ registry.py           # 类别主表统一加载（带缓存）
│  ├─ data/class_registry.csv  # 类别主表（class_id/class_key/display_name/category/active）
│  ├─ models/                  # 权重目录（.gitignore，不进 Git，走 GitHub Release）
│  ├─ utils/mlnlog.py          # 日志系统（彩色控制台 + 文件持久化）
│  ├─ modules/                 # 智能句读算法（阶段2实现）
│  └─ logs/                    # 运行日志输出
├─ frontend/
│  └─ src/
│     ├─ api/index.js          # axios 接口统一封装
│     ├─ views/SingleChar.vue  # 单减字识别页（后端优先/演示兜底）
│     ├─ views/WholeSheet.vue  # 整谱打谱页（后端优先/演示兜底）
│     └─ components/SheetCanvas.vue  # 谱图画布（选框/拖框/删框/画框）
├─ data/dataset/               # 训练数据集（图片走网盘，不进 Git）
├─ scripts/                    # Colab 训练 Notebook
└─ docs/                       # 接口契约、架构、句读规则手册、近期规划
```

---

## 二、环境准备（首次）

```powershell
# 后端虚拟环境
conda create -n lingxian python=3.10 -y
conda activate lingxian

# 安装后端依赖（假模型阶段只需这些）
pip install -r requirements.txt

# 前端依赖（已装过可跳过）
cd frontend
npm config set registry https://registry.npmmirror.com   # 国内加速，只需一次
npm install
```

---

## 三、启动（开两个终端）

**终端 1 — 后端：**

```powershell
conda activate lingxian
cd backend
python main.py
# 看到 Uvicorn running on http://127.0.0.1:8001 即成功
# 接口文档：http://127.0.0.1:8001/docs
```

**终端 2 — 前端：**

```powershell
cd frontend
npm run dev
# 浏览器打开 http://127.0.0.1:5173
```

> 前端已配置 `/api` 代理到 `8001`，无需处理跨域。
> **双模型版不再自动生成演示数据**：后端或权重未就绪时页面会明确提醒，可手动添加/修正框；正式比赛展示必须核实两个模型状态，避免误把旧演示数据当作模型能力。

---

## 四、功能与接口

| 功能 | 接口 | 说明 |
| --- | --- | --- |
| 单减字识别 | `POST /api/char/predict` | 上传单字图，返回 Top-3 候选 + 指法解析 |
| 整谱打谱 | `POST /api/sheet/upload` | 上传整页谱，返回检测框、逐框候选与解析 |
| 人工修正 | `POST /api/sheet/correct` | 记录人工修正（V1 占位） |
| 知识库 | `GET /api/knowledge/library`、`/detail/{key}`、`/search`、`/registry` | 减字语义查询 |
| 智能句读 | `POST /api/judou/segment` | 输入 class_key 序列，输出 C/S/L/E/U（V1 假规则） |

---

## 五、接入真实权重（双模型版，替代旧 V1 单模型）

模型线需同时交付：

1. `backend/models/best.pt`：**单类别减字区域检测** YOLO11n（类名须为 `jianzi`）；
2. `backend/models/stage2_best.pth`：八字段 ResNet18 多任务分类权重，内含 vocab，不是旧单输出 `resnet18_qin.pth`；
3. 相应的独立测试结果和训练版本信息。

安装后端推理依赖后重启：

```powershell
python -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
python -m pip install -r requirements.txt
cd backend
python main.py
```

`GET /api/sheet/model-status` 应显示两个 `available: true`。默认只产生 **待人工复核的指法属性候选**；旧25类知识库仍可通过手动 `class_key` 检索，但模型不会凭单类别检测 id 猜完整指法。具体步骤见 [双模型接入与验收](docs/双模型接入_人工复核与验收.md)。

**权重不进 Git**：单独放置或由模型线发布，不随源码上传。

---

## 六、常见问题

- **端口被占用**：后端改 `uvicorn main:app --reload --port 8002`，同步改 `frontend/vite.config.js` 代理目标。
- **npm install 卡住**：确认已设淘宝镜像 `npm config get registry`。
- **ModuleNotFoundError**：确认已 `conda activate lingxian` 且在项目根执行过 `pip install -r requirements.txt`。
- **后端没有模型候选**：检查 `/api/sheet/model-status` 和两个权重是否放对路径，不再把演示输出当成真实结果。
- **整谱未出框**：规则检测对图片质量敏感，换背景干净、字块清晰、无大段批注的谱图。
- **中文路径报错**：项目路径保持纯英文，勿放在含中文的父目录下。
