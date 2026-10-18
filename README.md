# 泠弦智谱 LingXianAI

古琴减字谱智能识别与打谱系统（全球校园 AI 算法精英大赛 · 泠弦智谱团队）。
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
> **后端未启动也能演示**：页面会自动回退内置演示数据，并以「演示数据」标签标明；
> 后端正常时标签显示「后端识别」。

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

## 五、接入真实权重（模型线交付后）

模型线需同时交付：

1. `resnet18_qin.pth` —— ResNet18 单字分类权重；
2. `class_mapping.json` —— 模型输出索引 → class_key 映射（缺失时按 class_registry.csv 顺序）；
3. 预处理规格说明 —— 输入尺寸 / 归一化 / 灰度或 RGB；
4. 版本评测说明 —— 准确率、混淆矩阵、训练数据量。

接入步骤：

```powershell
# 1. 安装推理依赖（CPU 版，仅首次）
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu

# 2. 权重放入（不进 Git）
#    backend/models/resnet18_qin.pth
#    backend/models/class_mapping.json
```

重启后端，`classifier.py` 会自动检测并加载权重；加载失败（未装 torch、
权重缺失或损坏、类别数不符）会记录告警并自动回退假模型，**接口与前端无需改动**。

权重文件较大，不提交 Git，通过 GitHub Release 或手动拷贝分发。

---

## 六、常见问题

- **端口被占用**：后端改 `uvicorn main:app --reload --port 8002`，同步改 `frontend/vite.config.js` 代理目标。
- **npm install 卡住**：确认已设淘宝镜像 `npm config get registry`。
- **ModuleNotFoundError**：确认已 `conda activate lingxian` 且在项目根执行过 `pip install -r requirements.txt`。
- **识别结果固定**：权重未接入时为假模型兜底，属正常现象。
- **整谱未出框**：规则检测对图片质量敏感，换背景干净、字块清晰、无大段批注的谱图。
- **中文路径报错**：项目路径保持纯英文，勿放在含中文的父目录下。
