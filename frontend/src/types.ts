export type AppTab = "chat-journal" | "insights" | "journal-history" | "journal-detail";

export type HistoryView = "list" | "detail";

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export interface ChatRequest {
  anon_id: string;
  message: string;
  history: ChatMessage[];
}

export interface ChatResponse {
  reply: string;
}

export interface PrecheckRequest {
  anon_id: string;
  body_feeling: string;
  need: string;
  emotion: string;
}

export interface PrecheckResponse {
  role: string;
  confidence: number;
  reasons: string;
}

export interface JournalRequest {
  anon_id: string;
  content: string;
  title?: string;
  mood?: string;
  weather?: string;
  entry_date?: string;  // Format: YYYY-MM-DD
}

export interface CrisisResult {
  risk_level: number;
  trigger: string;
  evidence: string[];
  confidence: number;
}

export interface TherapyRound {
  text: string;
  raw_json: Record<string, any>;
}

export interface JournalResponse {
  risk: CrisisResult;
  rounds: Partial<Record<"b1" | "b2" | "b3", TherapyRound>>;
  session_id?: string;
  round_index?: number;
}

export interface InsightItem {
  date: string;
  emotion_label?: string | null;
  risk_level?: number | null;
  summary: string;
}

export interface InsightsRequest {
  anon_id: string;
}

export interface InsightsResponse {
  total_entries: number;
  current_streak: number;
  top_mood: string;
  emotion_distribution: Record<string, number>;
  risk_distribution: Record<string, number>;
  timeline: InsightItem[];
  llm_summary: string;
  emotional_patterns: string;
  common_themes: string;
  growth_observations: string;
  recommendations: string;
  affirmation: string;
  focus_points: string[];
  analysis_history: string[];
}

// ========== Therapy Session Types ==========

export interface GatingDecision {
  decision: "READY_FOR_B2" | "STAY_IN_B1" | "READY_FOR_B3" | "STAY_IN_B2";
  reason: string;
  evidence: string[];
  followup_style: string;
}

export interface JournalSubmitResponse {
  risk: CrisisResult;
  rounds: Partial<Record<"b1" | "b2" | "b3", TherapyRound>>;
}

export interface ChatContinueRequest {
  session_id: string;
  user_message: string;
}

export interface ChatContinueResponse {
  assistant_message: string;
  round_index: number;
  status: "active" | "completed";
  gating_decision?: GatingDecision;
}

export interface TherapySessionInfo {
  session_id: string;
  entry_id: number;
  assistant_message: string;
  round_index: number;
  risk: CrisisResult;
  emotion_label: string;
  selected_role: string;
  status: string;
}

// ========== History Types ==========

export interface JournalHistoryItem {
  entry_id: number;
  entry_date?: string;
  title?: string;
  content?: string;
  mood?: string;
  weather?: string;
  preview: string;
  status?: "draft" | "completed";
}

export interface JournalHistoryResponse {
  entries: JournalHistoryItem[];
  total: number;
}

export interface JournalEntryResponse {
  entry_id: number;
  entry_date?: string;
  title?: string;
  content: string;
  mood?: string;
  weather?: string;
  emotion_label?: string;
  risk_level?: number;
  created_at: string;
  status?: "draft" | "completed";
}

export interface JournalFilterParams {
  date_from?: string;
  date_to?: string;
  mood?: string;
}

export interface JournalChatMessage {
  role: "user" | "assistant";
  content: string;
  mode?: string;
}

export interface JournalDetailResponse {
  entry: JournalEntryResponse;
  chat_history: JournalChatMessage[];
}
