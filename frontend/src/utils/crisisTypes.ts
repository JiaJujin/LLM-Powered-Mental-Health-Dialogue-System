/**
 * Crisis alert types — shared between the frontend app and dashboard.
 */

export type CrisisLevel = "none" | "low" | "medium" | "high";

export interface CrisisAlert {
  id: string;
  timestamp: string;          // ISO 8601
  source: "diary" | "chatbot";
  userId: string;
  textSnippet: string;        // first 100 chars of the triggering text
  matchedThemes: string[];    // e.g. ["hopelessness", "suicidal ideation"]
  reasoning: string;          // LLM's brief explanation
  level: Exclude<CrisisLevel, "none">;  // only non-none levels are stored
  isRead: boolean;
}
