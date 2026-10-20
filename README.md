# 泠弦智谱 LingXianAI

古琴减字谱智能识别与打谱系统，面向古琴学习者，提供**单减字识别、指法解析、整谱打谱、节奏（句读）划分**。

- 前端：Vue3 + Element-Plus + Vite（国风宣纸主题），端口 `5173`
- 后端：FastAPI + Uvicorn，端口 `8001`
- 架构：**纯本地两阶段推理，无任何外网云API依赖**，CPU即可运行

> 训练在GPU环境完成，产出权重后下载到本地`backend/models/`，训练与推理解耦。

---

## 一、目录结构
```
LingXian_AI_V1.0/
├─ backend/
│  ├─ main.py                  # FastAPI入口
│  ├─ api/                     # 路由层：single_char / whole_sheet / knowledge / judou
│  ├─ core/config.py           # 全局路径配置
│  ├─ service/
│  │  ├─ yolo_infer.py         # Stage1：YOLO减字框检测
│  │  ├─ stage2_infer.py       # Stage2：ResNet18多头指法属性识别
│  │  ├─ parser.py             # 减字key解析，输出中文释义
│  │  ├─ registry.py           # 类别注册表加载
│  │  └─ correction_store.py   # 人工修正持久化
│  ├─ data/class_registry.csv  # 类别主表（138类，覆盖散音/按音/装饰音/复合音）
│  ├─ models/                  # 权重目录（.gitignore，不进Git）
│  ├─ utils/mlnlog.py          # 统一日志系统
│  ├─ feedback.txt             # 人工修正反馈记录（Git跟踪，供开发团队核查）
│  └─ modules/                 # 句读规则引擎
├─ frontend/
│  └─ src/
│     ├─ api/index.js          # 接口封装
│     ├─ views/                # 四个功能页面
│     └─ components/SheetCanvas.vue # 谱图画布
├─ scripts/                    # 训练Notebook
└─ docs/                       # 架构、接口契约、句读规则文档
```

---

## 二、环境准备
```powershell
# 1. 创建虚拟环境
conda create -n lingxian python=3.10 -y
conda activate lingxian

# 2. 安装后端依赖
pip install -r requirements.txt
# 安装CPU版PyTorch（避免下载CUDA大包）
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu

# 3. 安装前端依赖
cd frontend
npm config set registry https://registry.npmmirror.com
npm install
```

---

## 三、启动（两个终端）
**终端1：后端**
```powershell
conda activate lingxian
cd backend
python main.py
# 看到 Application startup complete 即启动成功
```

**终端2：前端**
```powershell
cd frontend
npm run dev
# 浏览器打开 http://127.0.0.1:5173
```

---

## 四、功能与接口
| 功能 | 接口 | 说明 |
| --- | --- | --- |
| 单减字识别 | `POST /api/char/predict` | 上传单字图，返回候选+中文指法释义 |
| 整谱打谱 | `POST /api/sheet/upload` | 上传整谱，返回检测框、逐框识别结果 |
| 人工修正反馈 | `POST /api/sheet/correct` | 识别错误手动修正，同时写入`corrections.json`和`feedback.txt` |
| 减字知识库 | `GET /api/knowledge/library` | 支持按散音/按音/装饰音/复合音筛选、关键词搜索 |
| 智能句读 | `POST /api/judou/segment` | V1纯本地规则引擎，V2将训练专用句读模型 |

> 模型加载失败、权重缺失时，接口直接返回「请联系开发人员检查」，不返回假数据、不调用云API兜底。

---

## 五、权重说明
需放入`backend/models/`两个权重：
1. `best.pt`：Stage1 YOLO检测权重，仅输出减字位置框
2. `stage2_best.pth`：Stage2多头ResNet18识别权重，输出指法/弦/徽/修饰音属性

权重不提交Git，通过GitHub Release分发。

---

## 六、常见问题
- 端口占用：后端启动加参数`--port 8002`，同步修改`vite.config.js`代理目标
- 网络报错：确认后端已启动，两个服务同时运行
- 识别失败：检查权重是否放置正确，环境依赖是否完整
- 路径问题：项目路径保持纯英文，避免中文路径导致的图像处理错误
