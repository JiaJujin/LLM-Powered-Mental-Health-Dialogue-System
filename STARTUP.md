# MindJournal AI - 啟動指南

## 前置要求

- Node.js (v18+)
- Python 3.8+
- npm 或 yarn

## 啟動步驟

### 1. 啟動後端

```bash
cd mindjournal-ai/backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

後端運行在：http://localhost:8000

### 2. 啟動前端

```bash
cd mindjournal-ai/frontend
npm install
npm run dev
```

前端運行在：http://localhost:5173

## 功能說明

### 治療對話流程 (重構後)

1. **Pre-check** - 填寫 3 個初始問題（可跳過）
2. **提交日記** - AI 只生成 B1 回覆（單輪回應）
3. **對話互動** - AI 根據回覆質量決定：
   - 停留在當前輪次（質量不足）
   - 晉級到下一輪 B2/B3（質量足夠）
4. **完成對話** - B3 完成後可繼續一般對話

### API 端點

| 端點 | 方法 | 說明 |
|------|------|------|
| `/api/precheck` | POST | 提交 Pre-check |
| `/api/journal` | POST | 提交日記（只返回 B1） |
| `/api/chat` | POST | 一般對話 |
| `/api/chat/continue` | POST | 治療對話繼續（帶閘道判斷） |
| `/api/insights` | POST | 獲取 14 天洞察 |

## 數據庫

首次啟動後端會自動創建 SQLite 數據庫 (`mindjournal.db`)。

新增表：
- `therapy_sessions` - 治療會話記錄
