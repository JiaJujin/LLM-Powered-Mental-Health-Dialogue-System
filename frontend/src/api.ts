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
  ChatContinueResponse
} from "./types";

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
