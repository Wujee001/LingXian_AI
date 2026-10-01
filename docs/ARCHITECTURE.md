# LingXianAI 项目架构文档

> **泠弦智研** —— 基于深度学习的古琴减字谱智能打谱系统
> 版本：V1.0 ｜ 更新日期：2026-09-22

---

## 一、项目定位

| 项       | 说明                                                         |
| -------- | ------------------------------------------------------------ |
| 项目目标 | 上传古琴减字谱图片 → 自动识别减字 → 解析演奏信息（左手弦/徽位、右手指法）→ 智能句读分句 |
| 产品形态 | 本地单机 Web 应用（不上云、不做手机端）                      |
| 技术策略 | **接口先行、假模型兜底、真权重到位后只替换 predict()**       |
| 竞赛定位 | 大学生算法竞赛原型 Demo，不追求工业级精度，优先可运行、可演示 |

---

## 二、技术栈

| 层       | 技术                               | 说明                    |
| -------- | ---------------------------------- | ----------------------- |
| 后端     | Python 3.10 + FastAPI + Uvicorn    | conda 环境名 `lingxian` |
| 前端     | Vue3 + Vite + Element-Plus         | 国风淡雅 UI             |
| 图像识别 | ResNet18 / MobileNetV3 迁移学习    | 模型线交付 .pth 权重    |
| 整谱检测 | D-FINE / RF-DETR（V2）             | 整图减字定位切割        |
| 句读模型 | 可解释 Baseline + 轻量 Transformer | 双模型消融对照          |
| 语义库   | jianzipu_lib.json                  | 减字 → 演奏信息         |
| 日志     | mlnlog.py                          | 彩色控制台 + 文件持久化 |

---

## 三、三层技术架构

```
┌─────────────────────────────────────────────────────────┐
│                    原始减字谱图片                          │
└──────────────────────────┬──────────────────────────────┘
                           ▼
┌──────────────────────────────────────────────────────────┐
│  第一层：演奏语义层（视觉 → 结构化）                        │
│  整谱检测（V2）→ 单字分类识别 → 查知识库                    │
│  输出：演奏状态 z_i = {左手, 右手, 弦, 徽, 散按泛, 动作}    │
└──────────────────────────┬──────────────────────────────┘
                           ▼
┌──────────────────────────────────────────────────────────┐
│  第二层：结构句读层（两类人工知识进入）                     │
│                                                           │
│  古琴状态转移 Δz_i              汉语言句读启发 q_i           │
│  （换弦/徽位变化/指法连续度）   （结构完整度/标志结构/歧义） │
│         │                            │                    │
│         └──────────┬─────────────────┘                    │
│                    ▼                                      │
│            特征融合 [z_i, Δz_i, q_i]                       │
└──────────────────────────┬──────────────────────────────┘
                           ▼
┌──────────────────────────────────────────────────────────┐
│  第三层：序列推断层（AI 学习上下文）                        │
│  轻量 Transformer → P(C), P(S), P(L), P(E)                │
│  决策引擎：maxP < τ → U（人工复核）                        │
└──────────────────────────────────────────────────────────┘
```

### C/S/L/E/U 边界标签

| 标签  | 全称        | 含义                                   |
| ----- | ----------- | -------------------------------------- |
| **C** | Continue    | 连续——不建议停顿，演奏连贯             |
| **S** | Short-pause | 短停——弱边界，非句末小停顿             |
| **L** | Long-pause  | 长停——强边界，非句末大停顿             |
| **E** | End-phrase  | 句末——完整谱乐句结束                   |
| **U** | Review      | 复核——非音乐标签，低置信或歧义时转人工 |

**约束条件**：`P(E) ≤ P(S) + P(L) + P(E)`，保证"不是边界却判为句末"的逻辑矛盾不出现。

---

## 四、目录结构

```
LingXian_AI_V1.0/
├── backend/                          # FastAPI 后端
│   ├── main.py                        # 入口（挂载路由 + CORS）
│   ├── __init__.py
│   │
│   ├── api/                           # 接口路由层
│   │   ├── single_char.py             # 单减字识别+解析（V1核心）
│   │   ├── whole_sheet.py             # 整谱打谱（V1占位，V2接检测）
│   │   ├── knowledge.py              # 知识库查询/浏览
│   │   ├── judou.py                  # 智能句读 /api/judou/segment
│   │   └── __init__.py
│   │
│   ├── core/                          # 配置与静态资源
│   │   ├── config.py                  # 全局配置（全部相对路径）
│   │   ├── jianzipu_lib.json          # 减字语义知识库
│   │   └── __init__.py
│   │
│   ├── service/                        # 业务逻辑层
│   │   ├── classifier.py              # ⭐图像分类器（唯一替换点 predict()）
│   │   ├── parser.py                 # 减字解析 → 演奏状态 z_i
│   │   ├── registry.py               # 类别注册表加载
│   │   └── __init__.py
│   │
│   ├── modules/                      # 智能句读算法模块
│   │   ├── state_transfer/            # 数学建模
│   │   │   ├── feature_extractor.py  # Δz_i 特征提取
│   │   │   ├── baseline_model.py     # 可解释基线（Logistic/规则）
│   │   │   └── __init__.py
│   │   ├── judou/                     # 汉语言句读启发
│   │   │   ├── rules.py              # 句读规则打分
│   │   │   ├── features.py           # q_i 句读启发向量
│   │   │   └── __init__.py
│   │   └── sequence/                 # 序列融合与决策
│   │       ├── fusion.py             # 特征融合 [z_i, Δz_i, q_i]
│   │       ├── transformer_model.py   # 轻量序列模型 → C/S/L/E
│   │       ├── decision.py           # 决策引擎（阈值+约束→U）
│   │       └── __init__.py
│   │
│   ├── data/
│   │   └── class_registry.csv        # ⭐类别主表（软件/模型共用）
│   ├── models/                       # 模型权重（.gitignore，走Release）
│   ├── temp_upload/                  # 上传临时目录（.gitignore）
│   ├── logs/                         # 运行日志（.gitignore）
│   └── utils/
│       ├── mlnlog.py                 # 日志系统
│       └── __init__.py
│
├── frontend/                         # Vue3 前端
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js                # /api 代理到 8001
│   └── src/
│       ├── main.js
│       ├── App.vue                   # 国风导航布局
│       ├── style.css                 # 宣纸+墨色+朱砂
│       ├── api/index.js              # axios 封装
│       ├── router/index.js           # /single /whole /judou
│       ├── views/
│       │   ├── SingleChar.vue        # 单减字解析（V1核心）
│       │   ├── WholeSheet.vue        # 整谱打谱（占位）
│       │   └── JudouSegment.vue     # 智能句读标注
│       └── components/
│
├── data/dataset/                     # 数据集图片（.gitignore，走网盘）
├── docs/                             # 项目文档
│   ├── 项目规划.md
│   ├── 接口契约.md
│   ├── 团队分工.md
│   └── 句读规则手册.md
├── scripts/
│   ├── train_colab.ipynb             # 单字分类训练（ResNet18）
│   └── train_sequence.ipynb         # 句读序列训练（消融对照）
├── tests/
├── .gitignore
├── requirements.txt
└── README.md
```

---

## 五、核心设计原则

### 1. 接口先行（唯一接缝）

```
backend/service/classifier.py
  └─ predict(image_path) → List[{label, confidence, display}]
```

- **假模型阶段**：返回固定候选，前端手动选字兜底
- **真模型阶段**：模型线交付 .pth 后，仅替换此函数内部，接口和前端不动

### 2. 视觉与乐理分离

- **视觉模型**只认字形，输出拼音 class_key
- **乐理**全部交给 `jianzipu_lib.json`（左手弦/徽 + 右手指法 + 释义）
- 模型不学乐理，`class_registry.csv` 为软件/模型共用唯一类别主表

### 3. 双模型消融对照（写论文用）

| 模型        | 输入             | 说明           |
| ----------- | ---------------- | -------------- |
| Baseline    | Δz_i             | 可解释、易复现 |
| Transformer | [z_i, Δz_i, q_i] | 学习长程上下文 |

两者对比：证明领域特征与序列建模各自贡献，无论谁高都可成结论。

### 4. 模型可插拔

`classifier.predict()`、`baseline_model`、`transformer_model` 均为独立替换点，上层接口和前端不动。

---

## 六、软件线 ↔ 模型线接缝契约

### 模型线交付 4 件套（缺一不可）

| #    | 交付物                            | 放置位置             |
| ---- | --------------------------------- | -------------------- |
| 1    | `best_model.pth`                  | `backend/models/`    |
| 2    | `class_mapping.json`              | `backend/models/`    |
| 3    | 预处理规格（224尺寸/归一化/灰度） | 写入 `classifier.py` |
| 4    | 版本评测说明（准确率/混淆矩阵）   | `docs/`              |

### 类别主表

`backend/data/class_registry.csv`：软件与模型共用唯一类别主表，`class_key` 用拼音编码，中文仅作显示。新增类别必须双方确认后再训练。

---

## 七、端口与启动

| 项           | 值                         |
| ------------ | -------------------------- |
| 后端 FastAPI | http://127.0.0.1:8001      |
| 前端 Vite    | http://127.0.0.1:5173      |
| API 文档     | http://127.0.0.1:8001/docs |

```bash
# 后端
conda activate lingxian
cd backend
uvicorn main:app --reload --host 127.0.0.1 --port 8001

# 前端
cd frontend
npm install
npm run dev
```

---

## 八、Git 协作模型

```
main（保护分支，只收 PR）
  └── dev（集成分支）
        ├── feature/single-char
        ├── feature/whole-sheet
        ├── feature/judou
        └── feature/model-integration
```

- 权重走 GitHub Release，不进 Git
- 数据集图片走网盘，不进 Git
- `class_registry.csv` 和 `jianzipu_lib.json` 进 Git

---

## 九、迭代路线

| 版本     | 内容                                                         |
| -------- | ------------------------------------------------------------ |
| **V1**   | 单减字识别+解析（假模型兜底）、知识库浏览、人工修正          |
| **V1.5** | 接入真模型权重、句读 Baseline（Logistic）跑通                |
| **V2**   | D-FINE/RF-DETR 整谱检测、批量识别、序列还原、Transformer 句读 |
| **V3**   | 万级数据集、手写古谱、MIDI 合成、多定弦支持                  |