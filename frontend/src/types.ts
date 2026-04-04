export type AppTab = "chat-journal" | "insights" | "journal-history" | "journal-detail" | "support" | "my-support" | "chat";

export type HistoryView = "list" | "detail";

export type JournalInputMode = "text" | "voice" | "image";

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export interface ChatRequest {
  anon_id: string;
  message: string;
  history: ChatMessage[];
  diary_content?: string;
  assigned_role?: string;
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
  source_type?: "text" | "voice" | "image";
  original_input_text?: string;
  source_file_path?: string;
  input_metadata?: Record<string, unknown>;
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
  // Cache freshness fields
  is_from_cache: boolean;
  cached_at: string | null;
  source_entry_count: number;
  latest_entry_id: number | null;
  is_fresh: boolean;
}

export interface CachedInsightsResponse {
  has_cache: boolean;
  is_fresh: boolean;
  cached_at: string | null;
  source_entry_count: number;
  latest_entry_id: number | null;
  analysis: InsightsResponse | null;
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
  source_type?: "text" | "voice" | "image";
  created_at?: string;
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
  source_type?: "text" | "voice" | "image";
  original_input_text?: string;
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

// ========== Multimodal Types ==========

export interface TranscribeResponse {
  transcript: string;
  language?: string;
  duration_seconds?: number;
  segments?: Array<{
    start: number;
    end: number;
    text: string;
  }>;
  warnings?: string[];
}

export interface OCRDiaryResponse {
  raw_text: string;
  clean_text: string;
  confidence?: number;
  warnings?: string[];
}

export interface JournalSubmitParams {
  content: string;
  title?: string;
  mood?: string;
  weather?: string;
  entry_date?: string;
  source_type?: "text" | "voice" | "image";
  original_input_text?: string;
  source_file_path?: string;
  input_metadata?: Record<string, unknown>;
}

// ========== Chat Page Types ==========

export interface ChatSessionListItem {
  session_id: string;
  title?: string | null;
  last_message_preview?: string | null;
  created_at: string;
  updated_at: string;
}

export interface ChatSessionDetail {
  session_id: string;
  anon_id: string;
  title?: string | null;
  diary_content?: string | null;
  messages: ChatSessionMessage[];
  created_at: string;
  updated_at: string;
}

export interface ChatSessionMessage {
  role: "user" | "assistant";
  content: string;
  created_at?: string;
}
