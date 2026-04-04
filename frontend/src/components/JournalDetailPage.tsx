import { useState, useEffect } from "react";
import { ArrowLeft, Calendar, MessageCircle, User, Bot } from "lucide-react";
import { fetchJournalDetail } from "../api";
import type { JournalDetailResponse, JournalChatMessage } from "../types";

interface Props {
  anonId: string;
  entryId: number;
  onBack: () => void;
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

// Strip HTML tags for safe display
function stripHtml(html: string): string {
  const doc = new DOMParser().parseFromString(html, "text/html");
  return doc.body.textContent || "";
}

export default function JournalDetailPage({ anonId, entryId, onBack }: Props) {
  const [data, setData] = useState<JournalDetailResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadDetail();
  }, [entryId]);

  async function loadDetail() {
    setLoading(true);
    try {
      const result = await fetchJournalDetail(entryId);
      setData(result);
    } catch (err) {
      console.error("Failed to load entry:", err);
    } finally {
      setLoading(false);
    }
  }

  if (loading) {
    return (
      <div className="journal-detail-page">
        <div className="detail-loading">Loading...</div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="journal-detail-page">
        <div className="detail-error">
          <p>Entry not found.</p>
          <button className="btn-back" onClick={onBack}>
            <ArrowLeft size={16} />
            Back to History
          </button>
        </div>
      </div>
    );
  }

  const { entry, chat_history } = data;

  return (
    <div className="journal-detail-page">
      <div className="detail-header">
        <button className="btn-back" onClick={onBack}>
          <ArrowLeft size={18} />
          Back
        </button>
      </div>

      <div className="detail-content">
        {/* Journal Entry Section */}
        <div className="detail-entry-card">
          <div className="detail-entry-meta">
            <span className="detail-date">
              <Calendar size={16} />
              {entry.entry_date
                ? new Date(entry.entry_date).toLocaleDateString("en-US", {
                    weekday: "long",
                    month: "long",
                    day: "numeric",
                    year: "numeric",
                  })
                : new Date(entry.created_at).toLocaleDateString("en-US", {
                    weekday: "long",
                    month: "long",
                    day: "numeric",
                    year: "numeric",
                  })}
            </span>
            {entry.mood && (
              <span className="detail-mood">
                {MOOD_EMOJI[entry.mood] || ""} {entry.mood}
              </span>
            )}
            {entry.weather && (
              <span className="detail-weather">{entry.weather}</span>
            )}
          </div>

          {entry.title && <h1 className="detail-title">{entry.title}</h1>}

          <div className="detail-body">
            {stripHtml(entry.content)}
          </div>
        </div>

        {/* Chat History Section */}
        <div className="detail-chat-section">
          <div className="detail-chat-header">
            <MessageCircle size={18} />
            <h2>Conversation</h2>
          </div>

          {chat_history.length === 0 ? (
            <div className="detail-chat-empty">
              <p>No conversation for this entry.</p>
            </div>
          ) : (
            <div className="detail-chat-messages">
              {chat_history.map((msg, idx) => (
                <div
                  key={idx}
                  className={`detail-chat-msg ${msg.role === "user" ? "detail-chat-msg--user" : "detail-chat-msg--assistant"}`}
                >
                  <div className="detail-chat-msg__icon">
                    {msg.role === "user" ? (
                      <User size={16} />
                    ) : (
                      <Bot size={16} />
                    )}
                  </div>
                  <div className="detail-chat-msg__content">
                    <div className="detail-chat-msg__label">
                      {msg.role === "user" ? "You" : "AI"}
                    </div>
                    <div className="detail-chat-msg__text">
                      {stripHtml(msg.content)}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
