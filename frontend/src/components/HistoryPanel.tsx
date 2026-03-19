import { useState, useEffect } from "react";
import { X, Calendar, ChevronRight } from "lucide-react";
import { fetchJournalHistory, fetchJournalEntry } from "../api";
import type { JournalHistoryItem, JournalEntryResponse } from "../types";

interface Props {
  anonId: string;
  isOpen: boolean;
  onClose: () => void;
  onSelectEntry: (entry: JournalEntryResponse) => void;
}

const MOOD_EMOJI: Record<string, string> = {
  Happy: "😊",
  Calm: "😌",
  Angry: "😠",
  Anxious: "😰",
  Sad: "😢",
  Excited: "🤩",
  Grateful: "🙏",
};

function formatDate(dateStr: string | null, createdAt: string): string {
  if (dateStr) {
    return new Date(dateStr).toLocaleDateString("en-US", {
      weekday: "short",
      month: "short",
      day: "numeric",
    });
  }
  return new Date(createdAt).toLocaleDateString("en-US", {
    weekday: "short",
    month: "short",
    day: "numeric",
  });
}

export default function HistoryPanel({ anonId, isOpen, onClose, onSelectEntry }: Props) {
  const [entries, setEntries] = useState<JournalHistoryItem[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (isOpen && anonId) {
      loadHistory();
    }
  }, [isOpen, anonId]);

  async function loadHistory() {
    setLoading(true);
    try {
      const data = await fetchJournalHistory(anonId);
      setEntries(data.entries);
    } catch (err) {
      console.error("Failed to load history:", err);
    } finally {
      setLoading(false);
    }
  }

  async function handleSelectEntry(entryId: number) {
    try {
      const entry = await fetchJournalEntry(entryId);
      onSelectEntry(entry);
    } catch (err) {
      console.error("Failed to load entry:", err);
    }
  }

  if (!isOpen) return null;

  return (
    <>
      <div className="history-overlay" onClick={onClose} />
      <div className="history-panel">
        <div className="history-header">
          <h3>Past Entries</h3>
          <button className="btn-close" onClick={onClose}>
            <X size={20} />
          </button>
        </div>

        <div className="history-content">
          {loading ? (
            <div className="history-loading">Loading...</div>
          ) : entries.length === 0 ? (
            <div className="history-empty">
              <p>No past entries yet.</p>
              <p className="empty-hint">Start writing today.</p>
            </div>
          ) : (
            <div className="history-list">
              {entries.map((entry) => (
                <button
                  key={entry.entry_id}
                  className="history-item"
                  onClick={() => handleSelectEntry(entry.entry_id)}
                >
                  <div className="history-item-left">
                    <span className="history-date">
                      <Calendar size={14} />
                      {formatDate(entry.entry_date, entry.preview)}
                    </span>
                    {entry.title ? (
                      <span className="history-title">{entry.title}</span>
                    ) : (
                      <span className="history-preview">{entry.preview}</span>
                    )}
                  </div>
                  <div className="history-item-right">
                    {entry.mood && (
                      <span className="history-mood">
                        {MOOD_EMOJI[entry.mood] || ""} {entry.mood}
                      </span>
                    )}
                    <ChevronRight size={16} className="chevron" />
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </>
  );
}
