import { useState, useEffect } from "react";
import { Calendar, ChevronLeft, Search, X } from "lucide-react";
import { fetchFilteredJournalHistory } from "../api";
import type { JournalHistoryItem, JournalFilterParams } from "../types";

interface Props {
  anonId: string;
  onViewDetail: (entryId: number) => void;
}

const MOOD_OPTIONS = [
  { value: "", label: "All Moods" },
  { value: "Happy", label: "😊 Happy" },
  { value: "Calm", label: "😌 Calm" },
  { value: "Angry", label: "😠 Angry" },
  { value: "Anxious", label: "😰 Anxious" },
  { value: "Sad", label: "😢 Sad" },
  { value: "Excited", label: "🤩 Excited" },
  { value: "Grateful", label: "🙏 Grateful" },
];

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
      year: "numeric",
    });
  }
  return new Date(createdAt).toLocaleDateString("en-US", {
    weekday: "short",
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

// Strip HTML tags for safe display
function stripHtml(html: string): string {
  const doc = new DOMParser().parseFromString(html, "text/html");
  return doc.body.textContent || "";
}

// Get preview text (first 100 chars, no HTML)
function getPreview(content?: string): string {
  if (!content) return "";
  const text = stripHtml(content);
  return text.length > 100 ? text.substring(0, 100) + "..." : text;
}

export default function HistoryPage({ anonId, onViewDetail }: Props) {
  const [entries, setEntries] = useState<JournalHistoryItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [filters, setFilters] = useState<JournalFilterParams>({
    date_from: "",
    date_to: "",
    mood: "",
  });
  const [showDateFilter, setShowDateFilter] = useState(false);

  useEffect(() => {
    loadHistory();
  }, [anonId, filters]);

  async function loadHistory() {
    setLoading(true);
    try {
      const data = await fetchFilteredJournalHistory(anonId, filters);
      setEntries(data.entries);
    } catch (err) {
      console.error("Failed to load history:", err);
    } finally {
      setLoading(false);
    }
  }

  const handleFilterChange = (key: keyof JournalFilterParams, value: string) => {
    setFilters((prev) => ({ ...prev, [key]: value }));
  };

  const clearFilters = () => {
    setFilters({ date_from: "", date_to: "", mood: "" });
  };

  const hasActiveFilters = filters.date_from || filters.date_to || filters.mood;

  return (
    <div className="history-page">
      <div className="history-page-header">
        <h1>Journal History</h1>
      </div>

      {/* Filter Bar */}
      <div className="history-filter-bar">
        {/* Mood Filter */}
        <div className="filter-group">
          <select
            className="filter-select"
            value={filters.mood}
            onChange={(e) => handleFilterChange("mood", e.target.value)}
          >
            {MOOD_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>

        {/* Date Filter Toggle */}
        <button
          className={`filter-toggle ${showDateFilter ? "active" : ""}`}
          onClick={() => setShowDateFilter(!showDateFilter)}
        >
          <Calendar size={16} />
          {filters.date_from || filters.date_to ? "Date (active)" : "Filter by Date"}
        </button>

        {/* Date Range Inputs */}
        {showDateFilter && (
          <div className="date-range-filters">
            <input
              type="date"
              className="filter-date-input"
              value={filters.date_from}
              onChange={(e) => handleFilterChange("date_from", e.target.value)}
              placeholder="From"
            />
            <span className="date-separator">to</span>
            <input
              type="date"
              className="filter-date-input"
              value={filters.date_to}
              onChange={(e) => handleFilterChange("date_to", e.target.value)}
              placeholder="To"
            />
          </div>
        )}

        {/* Clear Filters */}
        {hasActiveFilters && (
          <button className="clear-filters-btn" onClick={clearFilters}>
            <X size={14} />
            Clear
          </button>
        )}
      </div>

      {/* Entries List */}
      <div className="history-entries">
        {loading ? (
          <div className="history-loading">Loading...</div>
        ) : entries.length === 0 ? (
          <div className="history-empty">
            <p>No journal entries found.</p>
            {hasActiveFilters && (
              <button className="clear-filters-link" onClick={clearFilters}>
                Clear filters
              </button>
            )}
          </div>
        ) : (
          <div className="history-cards">
            {entries.map((entry) => (
              <button
                key={entry.entry_id}
                className="history-card"
                onClick={() => onViewDetail(entry.entry_id)}
              >
                <div className="history-card-header">
                  <span className="history-card-date">
                    <Calendar size={14} />
                    {formatDate(entry.entry_date, entry.created_at || "")}
                  </span>
                  {entry.mood && (
                    <span className="history-card-mood">
                      {MOOD_EMOJI[entry.mood] || ""} {entry.mood}
                    </span>
                  )}
                </div>

                {entry.title && (
                  <h3 className="history-card-title">{entry.title}</h3>
                )}

                <p className="history-card-preview">
                  {getPreview(entry.content) || entry.preview}
                </p>

                <div className="history-card-footer">
                  <span className="history-card-chevron">
                    View entry
                    <ChevronLeft size={14} className="chevron-flip" />
                  </span>
                </div>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
