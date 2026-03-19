export function getOrCreateAnonId() {
  const key = "mindjournal_anon_id";
  const saved = localStorage.getItem(key);
  if (saved) return saved;

  const newId = crypto.randomUUID();
  localStorage.setItem(key, newId);
  return newId;
}

export function formatLabel(label?: string | null) {
  if (!label) return "Unknown";
  return label;
}
