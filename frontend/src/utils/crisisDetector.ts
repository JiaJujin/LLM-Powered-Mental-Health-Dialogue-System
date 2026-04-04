/**
 * Crisis intent detection via LLM-backed backend API.
 *
 * `detectCrisis(text, source, userId)` → `Promise<boolean>`
 * Returns true only when a non-none crisis level is detected.
 * Fails silently — never blocks the user's flow.
 *
 * Fire-and-forget usage:
 *   detectCrisis(text, 'diary', userId).then(triggered => {
 *     if (triggered) { setShowBanner(true); addNotification(...); }
 *   });
 */

const API_BASE = import.meta.env.VITE_API_BASE_URL || "/api";

interface ClassifyResponse {
  triggered: boolean;
  level: "none" | "low" | "medium" | "high";
  reasoning: string;
  matched_themes: string[];
}

/**
 * Check whether user input triggers a non-none crisis level.
 *
 * @param text    The user's diary text or chat message.
 * @param source  "diary" or "chatbot" — determines where the alert originated.
 * @param userId  Anonymous user identifier.
 * @returns        true if crisis detected (level = low/medium/high), false otherwise.
 */
export async function detectCrisis(
  text: string,
  source: "diary" | "chatbot",
  userId: string
): Promise<boolean> {
  if (text.trim().length < 5) return false;

  try {
    const res = await fetch(`${API_BASE}/crisis/classify`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, source, user_id: userId }),
    });
    if (!res.ok) return false;
    const data: ClassifyResponse = await res.json();
    return data.triggered === true && data.level !== "none";
  } catch {
    return false;
  }
}
