export function getOrCreateAnonId() {
  const key = "mindjournal_anon_id";
  const newId = () => crypto.randomUUID();

  try {
    const saved = localStorage.getItem(key);
    if (saved) return saved;
    const id = newId();
    localStorage.setItem(key, id);
    return id;
  } catch {
    try {
      const saved = sessionStorage.getItem(key);
      if (saved) return saved;
      const id = newId();
      sessionStorage.setItem(key, id);
      return id;
    } catch {
      return `anon_${newId()}`;
    }
  }
}

// -----------------------------------------------------------------------
// Precheck localStorage helpers
// -----------------------------------------------------------------------
const PRECHECK_STORAGE_KEY = "heaut_prechecked";
const PRECHECK_EXPIRY_MS = 24 * 60 * 60 * 1000; // 24 hours

export interface PrecheckStoredData {
  assigned_role: string;
  completed_at: string; // ISO timestamp
}

export function getStoredPrecheck(): PrecheckStoredData | null {
  try {
    const raw = localStorage.getItem(PRECHECK_STORAGE_KEY);
    if (!raw) return null;
    const parsed: PrecheckStoredData = JSON.parse(raw);
    const elapsed = Date.now() - new Date(parsed.completed_at).getTime();
    if (elapsed > PRECHECK_EXPIRY_MS) {
      localStorage.removeItem(PRECHECK_STORAGE_KEY);
      return null;
    }
    return parsed;
  } catch {
    return null;
  }
}

export function savePrecheckResult(role: string): void {
  try {
    const data: PrecheckStoredData = {
      assigned_role: role,
      completed_at: new Date().toISOString(),
    };
    localStorage.setItem(PRECHECK_STORAGE_KEY, JSON.stringify(data));
  } catch {
    // storage unavailable
  }
}

export function clearPrecheckResult(): void {
  try {
    localStorage.removeItem(PRECHECK_STORAGE_KEY);
  } catch {
    // storage unavailable
  }
}

/**
 * Convert snake_case or camelCase role names to a readable Title Case string.
 * e.g. "emotional_support" → "Emotional Support"
 *      "active_listening"   → "Active Listening"
 *      "GeneralSupport"    → "General Support"
 */
export function formatRoleName(role: string): string {
  if (!role) return "General Support";
  return role
    .replace(/_/g, " ")
    .replace(/([a-z])([A-Z])/g, "$1 $2")
    .split(" ")
    .filter(Boolean)
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

export function formatLabel(label?: string | null) {
  if (!label) return "Unknown";
  return label;
}
