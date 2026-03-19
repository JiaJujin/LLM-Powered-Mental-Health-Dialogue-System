# MindJournal AI

> An AI-powered mental health journaling application that combines reflective journaling with structured therapeutic conversations, powered by large language models.

> 一个由 AI 驱动的心理健康日记应用，将反思性日记与结构化治疗对话相结合，由大语言模型提供支持。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## Overview 概览

MindJournal AI is a privacy-first mental wellness companion that helps users process their thoughts through guided journaling and multi-stage AI therapeutic conversations. The app uses the **Nvidia Nemotron 3 Super** model via the OpenRouter API to deliver structured, evidence-informed psychological support without replacing professional care.

MindJournal AI 是一个注重隐私的心理健康伴侣，通过引导式日记和多阶段 AI 治疗对话帮助用户梳理思绪。该应用通过 OpenRouter API 使用 **Nvidia Nemotron 3 Super** 模型，提供结构化的、有循证依据的心理支持，且不替代专业诊疗。

Key principles 核心原则:
- **No diagnosis 不做诊断** — the AI never provides clinical diagnoses AI 不会提供临床诊断
- **No medical advice 不提供医疗建议** — no medication recommendations or treatment suggestions 不提供用药建议或治疗方案
- **Crisis safety 危机安全保障** — built-in risk detection with human support escalation 内置风险检测与人工支持升级机制
- **Privacy-first 隐私优先** — anonymous user IDs, local SQLite storage, no data sharing 匿名用户 ID、本地 SQLite 存储、不共享数据

---

## Features 功能

### Journal Entry & Analysis 日记记录与分析
- Write journal entries with mood and weather tags 用心情和天气标签写日记
- AI-powered emotion classification on every submission 提交时自动进行 AI 情绪分类
- Real-time risk detection with 3-level severity scoring 实时风险检测，分为 3 级严重程度
- Automatic reflective first-response (B1) after submission 提交后自动生成反思性首次回复（B1）

### Multi-Stage Therapeutic Conversation 多阶段治疗对话

The app uses a **3-stage gated therapy model** built on evidence-based approaches:

该应用使用基于循证方法的**三阶段门控治疗模型**：

| Stage 阶段 | Name 名称 | Approach 方法 | Trigger 触发条件 |
|-------|------|----------|--------|
| **B1** | Reflective Listening 反思性倾听 | Person-centered validation and empathic reflection 以人为中心的接纳与共情回应 | Always first 始终为第一步 |
| **B2** | Cognitive Clarification 认知澄清 | Socratic questioning to identify cognitive distortions 苏格拉底式提问以识别认知扭曲 | After gating check 通过门控检查后 |
| **B3** | Values & Commitment 价值观与承诺 | ACT-based defusion and value connection 基于 ACT 的解离技术与价值观连接 | After second gating check 通过第二次门控检查后 |

Each transition between stages requires an AI **gating decision** that evaluates whether the user is ready for deeper engagement.

每个阶段之间的转换都需要 AI 进行**门控决策**，评估用户是否准备好进行更深入的互动。

### Pre-Check Role Matching 提交前角色匹配
Before each journal submission, users describe their body feelings, needs, and emotions. The AI selects the most appropriate supportive role:

在每次提交日记前，用户描述身体感受、需求和情绪。AI 会选择最合适的支持角色：

- **Emotional Support 情感支持** — validation and empathy 接纳与共情
- **Clarify Thinking 思维澄清** — cognitive restructuring 认知重构
- **Meta Reflection 元反思** — observer perspective 观察者视角

### 14-Day Mental Health Insights 14 天心理健康洞察

An AI-generated dashboard summarizing:

AI 生成的数据仪表板，包含以下内容：

- Total entries and current journaling streak 记录总数与当前连续记录天数
- Emotion and risk distribution charts 情绪与风险分布图表
- Overall emotional summary 整体情绪摘要
- Key patterns and recurring themes 关键模式与反复出现的主题
- Growth moments and positive observations 成长时刻与积极观察
- Gentle, non-prescriptive recommendations 温和的、非指导性的建议
- **Affirmation** — a warm, personalized encouragement **肯定语** — 温暖、个性化的鼓励
- Focus points for self-reflection 自我反思的焦点

### Journal History 日记历史
- Browse all past journal entries 浏览所有历史日记
- Filter by date and mood 按日期和心情筛选
- Click into any entry to view full content and its chatbot conversation 点击任意日记查看完整内容及聊天对话

### Crisis Detection & Safety 危机检测与安全

Risk-level classification on every entry:

每次记录都有风险等级分类：

- **Level 1 等级 1** — Low risk, normal AI support proceeds 低风险，AI 正常支持
- **Level 2 等级 2** — Medium risk, AI proceeds with caution and supportive tone 中等风险，AI 谨慎推进，语气温和支持
- **Level 3 等级 3** — High risk, AI therapy stops and human support resources are shown 高风险，AI 治疗停止，显示人工支持资源

---

## Architecture 架构

```
┌─────────────────────────────────────────────────────────┐
│                   Frontend (React 19)                   │
│              http://localhost:5173                      │
│  ┌──────────────┐  ┌───────────────┐  ┌─────────────┐ │
│  │ JournalPanel │  │   ChatPanel   │  │InsightsPage │ │
│  └──────────────┘  └───────────────┘  └─────────────┘ │
│         ▲ Vite Proxy (dev) / Nginx (prod)              │
└─────────┬───────────────────────────────────────────────┘
          │ HTTP REST API  /api/*
          ▼
┌─────────────────────────────────────────────────────────┐
│                   Backend (FastAPI)                     │
│              http://localhost:8000                      │
│  ┌─────────────────────────────────────────────────────┐│
│  │             TherapyAgent (therapy_agent.py)          ││
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐         ││
│  │  │ PreCheck │  │ Journal  │  │ Insights │         ││
│  │  │  Router  │  │  Router  │  │  Router  │         ││
│  │  └──────────┘  └──────────┘  └──────────┘         ││
│  └─────────────────────────────────────────────────────┘│
│            │ Structured LLM calls via OpenRouter        │
│            ▼                                            │
│  ┌─────────────────────────────────────────────────────┐│
│  │      OpenRouter API → Nvidia Nemotron 3 Super       ││
│  │   https://openrouter.ai/api/v1/chat/completions     ││
│  └─────────────────────────────────────────────────────┘│
│            │ SQLAlchemy ORM                             │
│            ▼                                            │
│  ┌─────────────────────────────────────────────────────┐│
│  │              SQLite (mindjournal.db)                ││
│  │  Users │ JournalEntries │ ChatHistory │ Sessions   ││
│  └─────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────┘
```

---

## Tech Stack 技术栈

| Layer 层级 | Technology 技术 |
|-------|-----------|
| Frontend 前端 | React 19, TypeScript, Vite 6 |
| UI Icons 图标 | Lucide React |
| Charts 图表 | Recharts |
| HTTP Client HTTP 客户端 | Axios |
| Backend 后端 | FastAPI (Python 3.10+) |
| LLM | OpenRouter API → Nvidia Nemotron 3 Super 120B (free tier 免费版) |
| Model ID 模型 ID | `nvidia/nemotron-3-super-120b-a12b:free` |
| Database 数据库 | SQLite + SQLAlchemy ORM |
| Data Validation 数据验证 | Pydantic v2 |
| Prompt Engineering 提示工程 | JSON Schema structured output + Jinja2 templates |

---

## Getting Started 快速开始

### Prerequisites 前置条件
- **Node.js** 18+
- **Python** 3.10+
- **OpenRouter API Key** — get one free at [openrouter.ai](https://openrouter.ai) 在 openrouter.ai 免费获取

### 1. Clone the Repository 克隆仓库

```bash
git clone <your-repo-url>
cd mindjournal-ai
```

### 2. Backend Setup 后端设置

```bash
cd backend

python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate

pip install -r requirements.txt

echo "OPENROUTER_API_KEY=sk-or-v1-your-key-here" > .env

uvicorn app.main:app --reload --port 8000
```

Backend runs at `http://localhost:8000`
后端运行在 `http://localhost:8000`

Interactive API docs at `http://localhost:8000/docs`
交互式 API 文档在 `http://localhost:8000/docs`

> The SQLite database `backend/mindjournal.db` is auto-created on first run — no manual migration needed.
> SQLite 数据库 `backend/mindjournal.db` 会在首次运行时自动创建，无需手动迁移。

### 3. Frontend Setup 前端设置

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at `http://localhost:5173`
前端运行在 `http://localhost:5173`

All `/api/*` requests are proxied to `http://localhost:8000` via Vite proxy.
所有 `/api/*` 请求通过 Vite 代理转发到 `http://localhost:8000`。

---

## Project Structure 项目结构

```
mindjournal-ai/
├── README.md
├── README.zh.md
├── .env.example
│
├── frontend/
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx
│   │   ├── api.ts
│   │   ├── types.ts
│   │   ├── styles.css
│   │   └── components/
│   │       ├── ChatJournalPage.tsx
│   │       ├── InsightsPage.tsx
│   │       ├── HistoryPage.tsx
│   │       ├── JournalDetailPage.tsx
│   │       ├── JournalPanel.tsx
│   │       ├── ChatPanel.tsx
│   │       ├── PrecheckModal.tsx
│   │       ├── RiskBanner.tsx
│   │       ├── MoodChartCard.tsx
│   │       ├── StatCard.tsx
│   │       ├── InsightSectionCard.tsx
│   │       ├── AnalysisHistoryCard.tsx
│   │       ├── HumanSupportCard.tsx
│   │       └── Sidebar.tsx
│   ├── package.json
│   └── vite.config.ts
│
└── backend/
    ├── .env
    ├── app/
    │   ├── main.py
    │   ├── config.py
    │   ├── database.py
    │   ├── models.py
    │   ├── schemas.py
    │   ├── therapy_agent.py
    │   ├── llm_client.py
    │   ├── llm_schemas.py
    │   ├── routers/
    │   │   ├── precheck.py
    │   │   ├── journal.py
    │   │   ├── insights.py
    │   │   ├── chat.py
    │   │   └── chat_continue.py
    │   └── prompts/
    │       ├── prompt_a_role.txt
    │       ├── prompt_b1.txt
    │       ├── prompt_b2.txt
    │       ├── prompt_b3.txt
    │       ├── prompt_c_crisis.txt
    │       ├── prompt_d_insights.txt
    │       ├── prompt_e_emotion.txt
    │       ├── prompt_gating_b1_b2.txt
    │       └── prompt_gating_b2_b3.txt
    └── requirements.txt
```

---

## API Reference API 参考

### `POST /api/precheck`

**Request 请求:**
```json
{
  "anon_id": "user-uuid",
  "body_feeling": "tight chest, restless",
  "need": "to feel heard",
  "emotion": "anxious"
}
```
**Response 响应:**
```json
{
  "role": "Emotional Support",
  "confidence": 0.87,
  "reasons": "User expresses high emotional intensity and is seeking validation..."
}
```

---

### `POST /api/journal`

**Request 请求:**
```json
{
  "anon_id": "user-uuid",
  "content": "I felt really overwhelmed at work today...",
  "title": "Overwhelmed at work",
  "mood": "Anxious",
  "weather": "Cloudy"
}
```
**Response 响应:**
```json
{
  "risk": {
    "risk_level": 1,
    "trigger": "General stress without crisis signals",
    "evidence": ["Work-related stress mentioned"],
    "confidence": 0.92
  },
  "rounds": {
    "b1": {
      "text": "It sounds like today at work was really intense for you..."
    }
  },
  "session_id": "sess-uuid",
  "round_index": 1
}
```

---

### `POST /api/chat/continue`

**Request 请求:**
```json
{
  "session_id": "sess-uuid",
  "user_message": "Yes, exactly. I just feel like I'm not good enough..."
}
```
**Response 响应:**
```json
{
  "assistant_message": "That feeling of not being good enough — can you tell me more about when this thought tends to show up?",
  "round_index": 2,
  "status": "active",
  "gating_decision": {
    "decision": "STAY_IN_B2",
    "reason": "User is engaging with cognitive content but needs more exploration...",
    "followup_style": "Clarify automatic thoughts"
  }
}
```

---

### `POST /api/insights`

**Request 请求:**
```json
{ "anon_id": "user-uuid" }
```
**Response 响应:**
```json
{
  "total_entries": 8,
  "current_streak": 4,
  "top_mood": "Anxious",
  "emotion_distribution": { "Anxious": 4, "Calm": 2, "Sad": 2 },
  "llm_summary": "The past two weeks show a pattern of work-related stress...",
  "emotional_patterns": "Anxiety peaks mid-week, with relative calm on weekends...",
  "growth_observations": "User is developing increased emotional vocabulary...",
  "recommendations": "Consider noting which mornings feel lighter than others...",
  "affirmation": "You showed up again today, and that takes real courage.",
  "focus_points": ["What triggers your Tuesday anxiety?", "Which activities bring relief?"]
}
```

---

## Database Schema 数据库结构

| Table 表 | Description 描述 |
|-------|-------------|
| `users` | Anonymous user records (`anon_id` = UUID) 匿名用户记录 |
| `prechecks` | Pre-check submissions and role assignments 提交前检查与角色分配 |
| `journal_entries` | Journal content, mood, weather, emotion label, risk level 日记内容、心情、天气、情绪标签、风险等级 |
| `chat_history` | Individual chat round messages 聊天回合消息 |
| `therapy_sessions` | Session state: round_index, status, conversation history 会话状态：回合索引、状态、对话历史 |
| `analysis_history` | Past insights reports 历史洞察报告 |

All tables include `created_at` timestamps. No personal identifying information is stored.
所有表都包含 `created_at` 时间戳。不存储任何个人身份信息。

---

## Production Deployment 生产环境部署

Build the frontend 构建前端:
```bash
cd frontend
npm run build
```

Nginx config Nginx 配置:
```nginx
server {
    listen 80;

    location / {
        root /path/to/frontend/dist;
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

## Safety & Ethical Design 安全与伦理设计

1. **No diagnosis 不做诊断** — AI avoids all clinical diagnostic language AI 避免使用所有临床诊断性语言
2. **No medication advice 不提供用药建议** — prompts forbid medication or treatment recommendations 提示词禁止药物或治疗建议
3. **Crisis escalation 危机升级** — Level 3 risk triggers immediate display of human support resources 等级 3 风险立即显示人工支持资源
4. **No self-harm methods 不讨论自残方法** — AI is instructed never to discuss means of self-harm AI 被指示绝不能讨论自残方式
5. **Anonymous by default 默认匿名** — no email, name, or identifying data collected 不收集邮箱、姓名或任何可识别数据

> **Disclaimer 免责声明:** This application does not replace professional mental health care. If you are experiencing a mental health crisis, please contact emergency services or a qualified mental health professional.
> 本应用不能替代专业心理健康护理。若您正处于心理健康危机中，请联系紧急服务或合格的心理健康专业人员。

---

## Configuration 配置

| Variable 变量 | Default 默认值 | Description 描述 |
|----------|---------|-------------|
| `OPENROUTER_API_KEY` | *(required 必填)* | Your OpenRouter API key 您的 OpenRouter API 密钥 |
| `OPENROUTER_BASE_URL` | `https://openrouter.ai/api/v1` | OpenRouter base URL OpenRouter 基础 URL |
| `NEMOTRON_MODEL` | `nvidia/nemotron-3-super-120b-a12b:free` | Model identifier 模型标识符 |
| `DATABASE_URL` | `sqlite:///./mindjournal.db` | Database connection string 数据库连接字符串 |

---

## License 许可证

This project is licensed under the [MIT License](https://opensource.org/licenses/MIT).
本项目基于 [MIT 许可证](https://opensource.org/licenses/MIT) 开源。
