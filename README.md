# MindJournal AI

> 一个注重隐私的 AI 心理健康日记伴侣，通过引导式日记记录与结构化治疗对话，帮助用户梳理情绪、觉察内心。由大语言模型驱动。

> A privacy-first AI mental wellness companion that combines guided journaling with structured therapeutic conversations, powered by large language models.

---

## 核心原则 | Core Principles

- **不做诊断** — AI 不会给出临床诊断
- **不做医疗建议** — 不提供用药或治疗方案建议
- **危机安全保障** — 内置三级风险检测，Level 3 触发人工支持资源展示
- **默认匿名** — 不收集邮箱、姓名等可识别信息，所有用户以随机 UUID 标识
- **本地优先** — 数据存储在本地 SQLite，不主动共享

- **No Diagnosis** — AI does not provide clinical diagnoses
- **No Medical Advice** — No medication or treatment recommendations
- **Crisis Safety** — Built-in three-level risk detection, Level 3 triggers human support resources
- **Anonymous by Default** — No email, name, or identifying info collected; users identified by random UUID
- **Local-First** — Data stored locally in SQLite, not shared proactively

> 本应用不能替代专业心理健康护理。若您正处于心理健康危机中，请联系紧急服务或合格的心理健康专业人员。

> This app cannot replace professional mental health care. If you are in a mental health crisis, please contact emergency services or a qualified mental health professional.

---

## 主要功能 | Key Features

### 日记记录与分析 | Journal Recording & Analysis
- 支持文字输入、手写图片 OCR 识别（GLM-OCR）、语音转文字三种输入方式
- 提交时自动进行情绪分类（Emotion Classification）
- 实时风险检测，分为三个等级：低风险（正常支持）→ 中风险（谨慎推进）→ 高风险（停止 AI 治疗，显示人工支持资源）
- 提交后自动生成反思性首次回复（B1 阶段）

- Supports three input methods: text, handwriting OCR (GLM-OCR), voice-to-text
- Auto emotion classification on submission (Emotion Classification)
- Real-time risk detection in three levels: Low (normal support) → Medium (proceed with caution) → High (stop AI therapy, show human support)
- Auto-generate reflective first response (B1 stage) after submission

### 语音输入 | Voice Input (ASR)
- 浏览器端录制音频，调用后端语音转文字服务
- 支持三种后端（按优先级自动切换）：
  1. **智谱 GLM-ASR-2512**（主要方案，无需额外 API Key）
  2. **OpenAI Whisper**（需要 `OPENAI_API_KEY`）
  3. **Google Speech Recognition**（免费备选，无需 Key，支持短音频 <60s）
- 支持语言：普通话、粤语、英语

- Browser-side audio recording, calling backend speech-to-text service
- Three backends supported (auto-fallback):
  1. **Zhipu GLM-ASR-2512** (primary, no extra API Key needed)
  2. **OpenAI Whisper** (requires `OPENAI_API_KEY`)
  3. **Google Speech Recognition** (free fallback, supports <60s audio)
- Supported languages: Mandarin, Cantonese, English

### 手写日记图片 OCR | Handwriting OCR
- 上传手写日记照片，自动提取文字（GLM-OCR via zai SDK）
- 提取后由用户确认/编辑，再进入日记分析流程
- 仅做文字识别，不做心理分析

- Upload handwritten journal photos, auto extract text (GLM-OCR via zai SDK)
- User confirms/edits extracted text before entering journal analysis
- Text recognition only, no psychological analysis

### Pre-Check 角色匹配 | Pre-Check Role Matching
- 每次提交日记前，用户描述身体感受、需求和情绪
- AI 选择最合适的支持角色：情感支持 / 思维澄清 / 元反思

- Before each journal submission, user describes physical feelings, needs, and emotions
- AI selects the most suitable support role: Emotional Support / Clarify Thinking / Meta Reflection

### 三阶段治疗对话 | Three-Stage Therapeutic Dialogue (B1 / B2 / B3)
- **B1 — 反思性倾听**：以人为中心的接纳与共情回应，始终为对话第一步
- **B2 — 认知澄清**：苏格拉底式提问，识别认知扭曲（需通过门控评估后进入）
- **B3 — 价值观与承诺**：基于 ACT 的解离技术与价值观连接（需二次门控）
- 各阶段转换由 AI 门控决策评估用户是否准备好深入互动

- **B1 — Reflective Listening**: Person-centered acceptance and empathic response, always the first step
- **B2 — Cognitive Clarification**: Socratic questioning, identifying cognitive distortions (enters after gate evaluation)
- **B3 — Values & Commitment**: ACT-based defusion techniques and values connection (requires second gate)
- Stage transitions evaluated by AI gate decisions

### 心理健康洞察 | Mental Health Insights
- AI 生成近 14 天的数据仪表板：记录总数、连续记录天数、情绪与风险分布图表
- 整体情绪摘要、反复出现的主题、成长观察
- 温和、非指导性的建议 + 每日肯定语 + 自我反思焦点
- 洞察报告保存至历史，可随时回顾
- 支持洞察缓存，避免重复生成

- AI generates 14-day data dashboard: total records, streak days, emotion and risk distribution charts
- Overall emotional summary, recurring themes, growth observations
- Gentle, non-directive suggestions + daily affirmation + self-reflection focus
- Insights reports saved to history for review
- Insights caching to avoid redundant generation

### 日记历史 | Journal History
- 浏览所有历史日记，按日期和心情标签筛选
- 点击任意日记查看完整内容及对应治疗对话记录

- Browse all historical journals, filter by date and mood tags
- Click any journal to view full content and corresponding therapeutic dialogue

### 独立聊天页面 | Standalone Chat Page
- 无需日记，直接与 AI 进行自由对话
- 支持会话持久化，刷新页面不丢失对话

- Chat with AI freely without writing a journal
- Conversation persistence, survive page refresh

### 危机检测与响应 | Crisis Detection & Response
- **双重检测机制**：实时关键词检测 + 提交时风险等级评估
- 实时危机关键词库（中英文），每次对话触发检测
- Level 3 触发 CrisisAlert 记录，显示人工支持资源

- **Dual detection**: Real-time keyword detection + submission-time risk assessment
- Real-time crisis keyword library (Chinese & English), triggers on every message
- Level 3 triggers CrisisAlert record, displays human support resources

### 支持资源系统 | Support Resources System
- 心理健康支持资源仪表板
- 个人支持页面（MySupport.tsx）
- 危机热线、人工支持卡片展示

- Mental health support resources dashboard
- Personal support page (MySupport.tsx)
- Crisis hotlines, human support card display

---

## 技术栈 | Tech Stack

| 层级 | Layer | 技术 | Technology |
|------|-------|------|------------|
| 前端 | Frontend | React 19, TypeScript, Vite 6 | React 19, TypeScript, Vite 6 |
| UI 图标 | UI Icons | Lucide React | Lucide React |
| 图表 | Charts | Recharts | Recharts |
| HTTP 客户端 | HTTP Client | Axios | Axios |
| 状态管理 | State | Zustand（前端）+ SQLite（持久化） | Zustand + SQLite |
| 后端 | Backend | FastAPI (Python 3.10+), Pydantic v2 | FastAPI, Pydantic v2 |
| 数据库 | Database | SQLite + SQLAlchemy ORM 2.0 | SQLite + SQLAlchemy ORM 2.0 |
| LLM | LLM | 智谱 BigModel API（支持微调模型切换） | Zhipu BigModel API (fine-tuned model switchable) |
| STT | STT | 智谱 GLM-ASR-2512（主）→ Whisper → Google Speech | GLM-ASR-2512 → Whisper → Google Speech |
| OCR | OCR | 智谱 GLM-OCR via zai SDK | GLM-OCR via zai SDK |

---

## 项目结构 | Project Structure

```
mindjournal-ai/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI 入口 | FastAPI entry point
│   │   ├── config.py            # 配置管理 | Configuration
│   │   ├── database.py          # SQLAlchemy engine | Database setup
│   │   ├── models.py            # ORM 模型（8张表）| ORM models (8 tables)
│   │   ├── schemas.py           # Pydantic 模型 | Pydantic models
│   │   ├── llm_client.py        # 智谱 API 客户端 | Zhipu API client
│   │   ├── llm_schemas.py       # JSON Schema 定义 | JSON Schema definitions
│   │   ├── therapy_agent.py     # 治疗代理 | Therapy agent
│   │   ├── routers/
│   │   │   ├── precheck.py      # 角色匹配 | Role matching
│   │   │   ├── journal.py       # 日记 CRUD + 提交 | Journal CRUD + submission
│   │   │   ├── chat.py          # 首次对话 | First dialogue
│   │   │   ├── chat_continue.py # 继续对话 | Continue dialogue
│   │   │   ├── chat_sessions.py # 会话管理 | Session management
│   │   │   ├── insights.py      # 洞察生成 | Insights generation
│   │   │   ├── crisis.py        # 危机相关 | Crisis related
│   │   │   └── multimodal.py   # ASR + OCR | Speech & OCR
│   │   ├── services/
│   │   │   ├── stt_service.py   # 语音转文字 | Speech-to-text
│   │   │   ├── ocr_service.py   # 图像识别 | Image recognition
│   │   │   └── language_utils.py # 语言工具 | Language utilities
│   │   └── prompts/             # System prompt 模板 | Prompt templates
│   ├── scripts/
│   │   └── generate_finetune_data.py  # 微调数据生成 | Fine-tune data generation
│   ├── requirements.txt
│   └── .env
│
├── frontend/
│   ├── src/
│   │   ├── App.tsx              # 主应用 | Main app
│   │   ├── api.ts              # API 调用 | API calls
│   │   ├── types.ts            # 类型定义 | Type definitions
│   │   ├── styles.css          # 全局样式 | Global styles
│   │   ├── hooks/
│   │   │   ├── useVoiceInput.ts     # 语音录制 | Voice recording
│   │   │   └── useStreamingChat.ts  # 流式对话 | Streaming chat
│   │   ├── components/          # 组件（30+个）| Components (30+)
│   │   ├── pages/               # 页面 | Pages
│   │   ├── store/               # 状态管理 | State management
│   │   └── utils/               # 工具函数 | Utilities
│   ├── package.json
│   └── vite.config.ts
│
├── scripts/                     # 工具脚本 | Utility scripts
├── STARTUP.md                   # 一键启动指南 | Quick start guide
├── 原理详解.md                  # 原理详解 | Technical details
├── PPT.md                      # PPT 讲解稿 | PPT script
├── README.md
└── ...
```

---

## 环境变量 | Environment Variables

在 `backend/.env` 中配置 | Configure in `backend/.env`:

| 变量 | Variable | 必填 | Required | 默认值 | Default | 说明 | Description |
|------|----------|------|----------|--------|---------|------|-------------|
| `ZHIPU_API_KEY` | ZHIPU_API_KEY | 是 | Yes | — | — | 智谱 API Key | Zhipu API Key |
| `ZHIPU_BASE_URL` | ZHIPU_BASE_URL | 否 | No | `https://open.bigmodel.cn/api/paas/v4` | URL | 智谱 API 地址 | Zhipu API URL |
| `ZHIPU_MODEL` | ZHIPU_MODEL | 否 | No | `glm-4.5-air` | Model | 模型名称 | Model name |
| `OPENAI_API_KEY` | OPENAI_API_KEY | STT 备选 | STT fallback | — | — | Whisper ASR | Whisper ASR |

---

## 快速启动 | Quick Start

### 前提条件 | Prerequisites

- **Node.js** 18+
- **Python** 3.10+
- **智谱 API Key** — 从 [bigmodel.cn](https://open.bigmodel.cn) 获取 | Get from [bigmodel.cn](https://open.bigmodel.cn)

### 后端 | Backend

```bash
cd backend

# 创建虚拟环境 | Create virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # macOS / Linux

# 安装依赖 | Install dependencies
pip install -r requirements.txt

# 配置 .env | Configure .env
# copy .env.example to .env and add your API key

# 启动服务 | Start server
uvicorn app.main:app --reload --port 8000
```

后端运行于 `http://localhost:8000`，API 文档：`http://localhost:8000/docs` | Backend runs at `http://localhost:8000`, docs at `http://localhost:8000/docs`

### 前端 | Frontend

```bash
cd frontend

npm install
npm run dev
```

前端运行于 `http://localhost:5173` | Frontend runs at `http://localhost:5173`

### 一键启动（Windows）| One-Click Start (Windows)

双击运行 `一键启动MindJournal.bat` | Double-click `一键启动MindJournal.bat`

---

## API 参考 | API Reference

### 健康检查 | Health Check
- `GET /api/health` — 健康检查 | Health check

### 日记 | Journal
- `POST /api/journal` — 日记提交 | Journal submission
- `GET /api/journal/history` — 日记历史 | Journal history
- `GET /api/journal/entry/{id}` — 单条日记 | Single entry
- `PUT /api/journal/{id}` — 更新日记 | Update entry
- `DELETE /api/journal/{id}` — 删除日记 | Delete entry

### Pre-Check
- `POST /api/precheck` — 角色匹配 | Role matching

### 对话 | Dialogue
- `POST /api/chat` — 首次对话 | First dialogue
- `POST /api/chat/continue` — 继续对话（流式）| Continue dialogue (streaming)

### 会话 | Sessions
- `GET /api/sessions/{anon_id}` — 会话列表 | Session list
- `POST /api/sessions` — 创建会话 | Create session
- `GET /api/sessions/{id}/detail` — 会话详情 | Session detail

### 洞察 | Insights
- `POST /api/insights` — 生成洞察 | Generate insights
- `GET /api/insights/{anon_id}` — 获取缓存洞察 | Get cached insights

### 多模态 | Multimodal
- `POST /api/transcribe` — 语音转文字 | Speech-to-text
- `POST /api/ocr-diary` — 图片 OCR | Image OCR

### 危机 | Crisis
- `POST /api/crisis/classify` — 危机分类 | Crisis classification
- `GET /api/crisis/resources` — 危机资源 | Crisis resources

---

## 主流水 | Streaming

对话使用 Server-Sent Events（SSE）流式输出 | Dialogue uses SSE streaming:

```
POST /api/chat/continue
→ event: chunk
→ data: {"content": "It sounds like..."}

→ event: done
→ data: {"round_index": 2, "status": "active"}
```

---

## 数据库模型 | Database Models

| 表名 | Table | 说明 | Description |
|------|-------|------|-------------|
| `users` | users | 匿名用户 | Anonymous users |
| `prechecks` | prechecks | Pre-Check 记录 | Pre-check records |
| `journal_entries` | journal_entries | 日记条目 | Journal entries |
| `therapy_sessions` | therapy_sessions | 治疗会话 | Therapy sessions |
| `chat_sessions` | chat_sessions | 独立会话 | Standalone sessions |
| `chat_history` | chat_history | 对话历史 | Chat history |
| `analysis_history` | analysis_history | 洞察历史 | Insights history |
| `crisis_alerts` | crisis_alerts | 危机警报 | Crisis alerts |

---

## 微调模型 | Fine-Tuned Models

项目支持使用微调模型提升对话质量 | Project supports fine-tuned models for better dialogue quality.

### 为什么需要微调 | Why Fine-Tuning?

MindJournal AI 是一款心理咨询对话 AI，核心场景是**引导用户记录日记并展开结构化心理治疗对话**。直接调用通用大模型存在以下问题：

| 问题 | 说明 |
|------|------|
| **角色一致性差** | 通用模型不知道自己是"心理咨询 AI"，回复风格飘忽 |
| **多角色切换困难** | 项目有 3 个治疗角色，通用模型难以准确切换 |
| **语言一致性** | 用户中英文混杂，通用模型有时中英混搭 |
| **回复长度失控** | 通用模型回复过长或过短，不符合产品规范 |
| **API 调用成本** | 每次对话都走 API 调用，微调后可部署成本更低 |

因此，我们对智谱 `glm-4-plus` 进行**监督微调（Supervised Fine-Tuning, SFT）**，让它学会 MindJournal AI 的专业对话风格。

### 微调数据集 | Fine-Tuning Dataset

**数据来源**：

```
总数据量：564 条对话
├── 真实用户对话（14 条，24.7%）
│   └── 来源：SQLite 数据库中的 chat_sessions / therapy_sessions
│
└── 合成数据（550 条，75.3%）
    └── 使用 glm-4.6 根据场景模板批量生成
    └── 三种角色各按比例生成
```

**三种治疗角色**：

| 角色 | System Prompt 核心指令 | 合成条数 | 示例场景 |
|------|----------------------|---------|---------|
| **陪我聊聊**（Emotional Support） | 接住情绪，先听先共情，不给建议 | 285 条 | 和妈妈吵架、失恋、工作压力 |
| **帮我理清**（Clarify Thinking） | 温和提问，帮助理清思路 | 138 条 | 职业选择困难、反复纠结的想法 |
| **拉开一点看**（Meta Reflection） | 生活比喻，助用户从更高视角观察 | 127 条 | 陷入负面思维循环、价值观探索 |

**数据格式（JSONL）**：

```json
{
  "messages": [
    {"role": "system", "content": "你是 MindJournal AI，一位温暖善解人意的心理咨询 AI...\n\n## 当前角色：陪我聊聊\n\n你的首要任务是接住情绪..."},
    {"role": "user", "content": "今天和妈妈吵架了，心里特别堵"},
    {"role": "assistant", "content": "听到你说今天和妈妈吵架了，那种心里特别堵的感觉真的很难受..."}
  ]
}
```

**质量控制**：

- 长度控制在 30–600 字之间
- 无乱码或异常 Unicode 字符
- 无"你应该…"、"你必须…"等指令式语气
- 无固定模板开头（如"谢谢你的分享"）
- 语言与用户输入一致

### 微调流程 | Fine-Tuning Process

**Step 1: 准备数据**
```
└── finetune_chat.jsonl（694 KB，564 条）
```

**Step 2: 上传数据集**
```
└── 登录 bigmodel.cn → 模型微调 → 创建数据集
└── 选择格式：JSONL → 上传文件 → 等待校验
```

**Step 3: 创建微调任务**

| 参数 | 值 |
|------|-----|
| 基础模型 | glm-4-plus |
| 训练集比例 | 80% / 10% / 10% |
| Epochs | 2 |
| Learning Rate | 1e-5 |
| Max Tokens | 350 |

**Step 4: 部署 & 获取模型 ID**
```
└── 平台提供微调后模型 ID
└── 修改 backend/.env 中的 ZHIPU_MODEL
```

### 部署切换 | Deployment

只需修改一行配置即可切换模型：

```env
# 微调模型
ZHIPU_MODEL=your-finetuned-model-id

# 通用模型（切回）
ZHIPU_MODEL=glm-4.6
```

### 预期效果 | Expected Results

| 维度 | 微调前（通用 glm-4.6） | 微调后 |
|------|----------------------|--------|
| 角色一致性 | 偶尔偏离"心理咨询 AI"角色 | 始终稳定在角色内 |
| 三角色切换 | 容易混淆角色指令 | 准确识别并切换 |
| 回复长度 | 过长或过短 | 稳定在 50–200 字 |
| 语言一致性 | 中英文偶尔混搭 | 与用户语言严格一致 |

### 技术架构回顾 | Architecture

```
                    ┌─────────────────────────────┐
                    │   用户对话流程               │
                    └──────────┬──────────────────┘
                               │
                    ┌──────────▼──────────────────┐
                    │  Pre-Check 角色匹配         │
                    │  (陪我聊聊/帮我理清/拉开一点看)│
                    └──────────┬──────────────────┘
                               │
         ┌─────────────────────┼─────────────────────┐
         │                     │                     │
┌────────▼────────┐  ┌────────▼────────┐  ┌────────▼────────┐
│  日记 + B1 反思  │  │   B2 认知澄清    │  │  B3 元反思/ACT  │
└─────────────────┘  └─────────────────┘  └─────────────────┘
         │                     │                     │
         └─────────────────────┼─────────────────────┘
                               │
                    ┌──────────▼──────────────────┐
                    │  微调后的 glm-4-plus          │
                    │  (角色一致 + 风格稳定)         │
                    └──────────────────────────────┘
```

### 隐私与伦理 | Privacy & Ethics

- **数据匿名化**：训练数据中不包含任何可识别个人身份的信息
- **安全边界**：AI 仅提供情感支持，不提供临床诊断或药物治疗建议
- **危机检测**：内置三级风险检测，高风险时显示人工支持资源
- **本地存储**：所有用户数据存储在本地 SQLite，不上传第三方

---

## 生产部署 | Production Deployment

### 构建前端 | Build Frontend

```bash
cd frontend
npm run build
```

### Nginx 配置 | Nginx Config

```nginx
server {
    listen 80;
    root /path/to/frontend/dist;
    try_files $uri $uri/ /index.html;

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
    }
}
```

### Railway 部署 | Railway Deployment

项目包含 `railway.json` 配置，支持一键部署到 Railway：

```bash
# 1. 连接 GitHub 仓库
# 2. Railway 自动检测 Dockerfile 构建
# 3. 配置环境变量
ZHIPU_API_KEY=your-api-key
ZHIPU_MODEL=glm-4.5-air
```

### Vercel 部署 | Vercel Deployment

项目包含 `vercel.json` 配置 | Project includes `vercel.json` config.

```bash
npm i -g vercel
cd backend && vercel
cd frontend && vercel
```

---

## 相关文档 | Related Documents

- [STARTUP.md](./STARTUP.md) — 一键启动指南 | Quick start guide
- [原理详解.md](./原理详解.md) — 技术原理详解 | Technical details
- [PPT.md](./PPT.md) — PPT 讲解稿 | PPT script

---

## 当前状态 | Current Status

### 已完成 | Completed
- 日记记录与分析 | Journal recording & analysis
- Pre-Check 角色匹配 | Pre-check role matching
- 三阶段治疗对话 | Three-stage therapeutic dialogue
- 心理健康洞察 | Mental health insights
- 语音输入 | Voice input
- 手写 OCR | Handwriting OCR
- 危机检测 | Crisis detection
- 日记历史 | Journal history
- 独立聊天页面 | Standalone chat
- 会话持久化 | Session persistence
- 支持资源系统 | Support resources

### 规划中 | In Progress
- 更丰富的洞察可视化 | Enhanced insights visualization
- 多语言界面 | Multi-language UI
- 导出功能 | Export functionality

---

## License

MIT License
