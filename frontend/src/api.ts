import axios from "axios";
import type {
  PrecheckRequest,
  PrecheckResponse,
  JournalRequest,
  JournalResponse,
  JournalHistoryResponse,
  JournalEntryResponse,
  JournalFilterParams,
  JournalDetailResponse,
  InsightsRequest,
  InsightsResponse,
  ChatRequest,
  ChatResponse,
  ChatContinueRequest,
  ChatContinueResponse,
  TranscribeResponse,
  OCRDiaryResponse,
} from "./types";
import type { CrisisAlert } from "./utils/crisisTypes";

// 开发时用相对路径走 Vite 代理，避免跨域；生产环境可设 VITE_API_BASE_URL
const API_BASE = import.meta.env.VITE_API_BASE_URL || "/api";

const client = axios.create({
  baseURL: API_BASE,
  timeout: 180000
});

export async function submitChat(payload: ChatRequest) {
  const { data } = await client.post<ChatResponse>("/chat", payload);
  return data;
}

export async function submitPrecheck(payload: PrecheckRequest) {
  const { data } = await client.post<PrecheckResponse>("/precheck", payload);
  return data;
}

export async function submitJournal(payload: JournalRequest) {
  const { data } = await client.post<JournalResponse>("/journal", payload);
  return data;
}

export async function fetchInsights(payload: InsightsRequest) {
  const { data } = await client.post<InsightsResponse>("/insights", payload);
  console.log("[ANALYSIS] fetchInsights response:", data);
  return data;
}

/** GET /api/insights/cached/{anon_id} — lightweight check: is there a fresh cached analysis? */
export async function fetchCachedInsights(anonId: string) {
  const { data } = await client.get<{
    has_cache: boolean;
    is_fresh: boolean;
    cached_at: string | null;
    source_entry_count: number;
    latest_entry_id: number | null;
    analysis: InsightsResponse | null;
  }>(`/insights/cached/${anonId}`);
  console.log("[CACHE] fetchCachedInsights:", data);
  return data;
}

/** GET /api/insights/{anon_id} — retrieve the cached analysis (no regeneration) */
export async function fetchCachedAnalysis(anonId: string): Promise<InsightsResponse | null> {
  try {
    const { data } = await client.get<InsightsResponse>(`/insights/${anonId}`);
    console.log("[CACHE_GET] fetchCachedAnalysis:", data);
    return data;
  } catch {
    return null;
  }
}

/** GET /api/insights/history/{anon_id}/{date} — fetch a specific historical analysis */
export async function fetchAnalysisByDate(anonId: string, date: string) {
  const { data } = await client.get(`/insights/history/${anonId}/${encodeURIComponent(date)}`);
  console.log("[ANALYSIS] fetchAnalysisByDate:", date, data);
  return data;
}

export async function continueChat(payload: ChatContinueRequest) {
  const { data } = await client.post<ChatContinueResponse>("/chat/continue", payload);
  return data;
}

export async function fetchJournalHistory(anonId: string) {
  const { data } = await client.get<JournalHistoryResponse>("/journal/history", {
    params: { anon_id: anonId }
  });
  return data;
}

export async function fetchJournalEntry(entryId: number) {
  const { data } = await client.get<JournalEntryResponse>(`/journal/entry/${entryId}`);
  return data;
}

export async function fetchFilteredJournalHistory(anonId: string, filters: JournalFilterParams) {
  const { data } = await client.get<JournalHistoryResponse>("/journal/history", {
    params: { anon_id: anonId, ...filters }
  });
  return data;
}

export async function fetchJournalDetail(entryId: number) {
  const { data } = await client.get<JournalDetailResponse>(`/journal/detail/${entryId}`);
  return data;
}

/**
 * GET /api/journal/{anon_id}/{date}
 * Returns today's journal entry (or 404 if none exists).
 */
export async function fetchTodayJournalEntry(
  anonId: string,
  date: string
): Promise<JournalEntryResponse | null> {
  try {
    const { data } = await client.get<JournalEntryResponse>(
      `/journal/${anonId}/${date}`
    );
    return data;
  } catch {
    return null; // silent — no entry for this date
  }
}

// ========== Chat Session Persistence APIs ==========

export interface ChatSessionMessage {
  role: "user" | "assistant";
  content: string;
  created_at?: string;
}

export interface ChatSession {
  session_id: string;
  anon_id: string;
  type?: string;
  title?: string;
  diary_content?: string;
  messages: ChatSessionMessage[];
  created_at: string;
  updated_at: string;
}

/** GET /api/chat/sessions/{anon_id}/latest — load or auto-create latest session */
export async function fetchLatestChatSession(anonId: string, type?: string): Promise<ChatSession | { session_id: string; created_at: string }> {
  const { data } = await client.get<ChatSession>(`/chat/sessions/${anonId}/latest`, {
    params: type ? { type } : undefined,
  });
  return data;
}

/** POST /api/chat/sessions — create a brand-new session */
export async function createChatSession(anonId: string, type?: string): Promise<{ session_id: string; created_at: string }> {
  const { data } = await client.post<{ session_id: string; created_at: string }>("/chat/sessions", {
    anon_id: anonId,
    type: type ?? "chat",
  });
  return data;
}

/** POST /api/chat/sessions/{session_id} — append a message to a session */
export async function appendChatMessage(
  sessionId: string,
  role: "user" | "assistant",
  content: string,
  diary_content?: string
): Promise<{ messages: ChatSessionMessage[] }> {
  const { data } = await client.post<{ messages: ChatSessionMessage[] }>(
    `/chat/sessions/${sessionId}`,
    { role, content, diary_content }
  );
  return data;
}

/** GET /api/chat/sessions/{anon_id} — list all sessions for a user */
export async function fetchAllChatSessions(anonId: string, type?: string): Promise<{ sessions: Array<{ session_id: string; title?: string; last_message_preview?: string | null; created_at: string; updated_at: string }> }> {
  const { data } = await client.get<{ sessions: Array<{ session_id: string; title?: string; last_message_preview?: string | null; created_at: string; updated_at: string }> }>(`/chat/sessions/${anonId}`, {
    params: type ? { type } : undefined,
  });
  return data;
}

/** GET /api/chat/sessions/{anon_id}/detail — full session with messages (for history load) */
export async function fetchChatSessionDetail(sessionId: string): Promise<ChatSession | null> {
  try {
    const { data } = await client.get<ChatSession>(`/chat/sessions/detail/${sessionId}`);
    return data;
  } catch {
    return null;
  }
}

/** PATCH /api/chat/sessions/{session_id}/title — update session title */
export async function updateChatSessionTitle(
  sessionId: string,
  title: string
): Promise<void> {
  await client.patch(`/chat/sessions/${sessionId}/title`, { title });
}

// ========== Multimodal Input APIs ==========

const MULTIMODAL_TIMEOUT = 120_000; // 2 min for OCR/STT

export async function transcribeAudio(audioBlob: Blob, filename: string): Promise<TranscribeResponse> {
  const formData = new FormData();
  formData.append("file", audioBlob, filename);
  const { data } = await client.post<TranscribeResponse>("/transcribe", formData, {
    headers: { "Content-Type": "multipart/form-data" },
    timeout: MULTIMODAL_TIMEOUT,
  });
  return data;
}

export async function ocrDiaryImage(imageBlob: Blob, filename: string): Promise<OCRDiaryResponse> {
  const formData = new FormData();
  formData.append("file", imageBlob, filename);
  const { data } = await client.post<OCRDiaryResponse>("/ocr-diary", formData, {
    headers: { "Content-Type": "multipart/form-data" },
    timeout: MULTIMODAL_TIMEOUT,
  });
  return data;
}

// ========== Crisis Detection API ==========

export interface CrisisClassifyRequest {
  text: string;
  source: "diary" | "chatbot";
  user_id: string;
}

export async function classifyCrisis(
  payload: CrisisClassifyRequest
): Promise<CrisisAlert | null> {
  try {
    const { data } = await client.post<{
      triggered: boolean;
      level: string;
      reasoning: string;
      matched_themes: string[];
    }>("/crisis/classify", payload, { timeout: 30_000 });
    if (!data.triggered || data.level === "none") return null;
    return {
      id: crypto.randomUUID(),
      timestamp: new Date().toISOString(),
      source: payload.source,
      userId: payload.user_id,
      textSnippet: payload.text.slice(0, 100),
      matchedThemes: data.matched_themes ?? [],
      reasoning: data.reasoning ?? "",
      level: data.level as CrisisAlert["level"],
      isRead: false,
    };
  } catch {
    return null;
  }
}
