/**
 * My Support — user-facing page
 *
 * Shows the user's assigned supporter and:
 * 1. Notification history (frontend-side, from useSupportNotifications)
 * 2. Crisis Support Records (fetched from GET /api/crisis-alerts/{userId})
 */

import { useEffect, useState, useCallback } from "react";
import { HeartHandshake, AlertTriangle, RefreshCw } from "lucide-react";
import { ASSIGNED_SUPPORTER } from "../utils/mockSupporter";
import { useSupportNotifications } from "../store/supportNotificationStore";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface CrisisAlertRecord {
  id: number;
  source: string;
  triggered_at: string;
  status: string;
  message_snippet: string;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatTime(iso: string): string {
  const date = new Date(iso);
  const now = new Date();
  const isToday = date.toDateString() === now.toDateString();
  const timeStr = date.toLocaleTimeString("en-US", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
  if (isToday) return `Today, ${timeStr}`;
  return (
    date.toLocaleDateString("en-US", { month: "short", day: "numeric" }) +
    `, ${timeStr}`
  );
}

function formatCrisisTime(iso: string): string {
  const d = new Date(iso);
  const months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
  const day = String(d.getDate()).padStart(2, "0");
  const month = months[d.getMonth()];
  const year = d.getFullYear();
  const hh = String(d.getHours()).padStart(2, "0");
  const mm = String(d.getMinutes()).padStart(2, "0");
  return `${month} ${day}, ${year} · ${hh}:${mm}`;
}

const STATUS_COLORS = {
  online: "#22c55e",
  busy: "#f59e0b",
  offline: "#9ca3af",
};

// ---------------------------------------------------------------------------
// Demo simulation (remove before production)
// ---------------------------------------------------------------------------

function SimulateButton() {
  const { addNotification } = useSupportNotifications();

  const simulate = () => {
    addNotification({
      id: crypto.randomUUID(),
      timestamp: new Date().toISOString(),
      source: Math.random() > 0.5 ? "diary" : "chat",
      message:
        Math.random() > 0.5
          ? "Your supporter was notified based on your diary entry."
          : "Your supporter was notified based on your conversation.",
      isRead: false,
    });
  };

  return (
    <button
      type="button"
      className="btn-demo-support"
      onClick={simulate}
      title="Demo only"
    >
      Simulate Notification
    </button>
  );
}

// ---------------------------------------------------------------------------
// Supporter card
// ---------------------------------------------------------------------------

function SupporterCard() {
  const supporter = ASSIGNED_SUPPORTER;
  const statusColor = STATUS_COLORS[supporter.status] ?? STATUS_COLORS.offline;

  return (
    <div className="my-support-supporter-card">
      {/* Avatar */}
      <div
        className="my-support-avatar"
        style={{ backgroundColor: supporter.avatarColor }}
        aria-hidden="true"
      >
        {supporter.initials}
      </div>

      {/* Info */}
      <div className="my-support-info">
        <h2 className="my-support-name">{supporter.fullName}</h2>
        <p className="my-support-role">{supporter.role}</p>
        <p className="my-support-dept">{supporter.department}</p>

        {/* Status */}
        <div className="my-support-status-row">
          <span
            className="my-support-status-dot"
            style={{ backgroundColor: statusColor }}
          />
          <span className="my-support-status-label">{supporter.statusLabel}</span>
        </div>

        {/* Bio */}
        <p className="my-support-bio">"{supporter.bio}"</p>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Notification history (frontend-side store)
// ---------------------------------------------------------------------------

function NotificationSection() {
  const { state } = useSupportNotifications();
  const { notifications } = state;

  return (
    <div className="my-support-notification-section">
      {notifications.length === 0 ? (
        <p className="my-support-notification-empty">No support records yet.</p>
      ) : (
        <ul className="my-support-list">
          {notifications.map((n) => (
            <li key={n.id} className="my-support-item">
              <span className="my-support-check" aria-label="Notified">
                ✓
              </span>
              <div className="my-support-item-body">
                <span className="my-support-item-source">
                  {n.source === "diary" ? "📓 Diary" : "💬 Chat"}
                </span>
                <p className="my-support-item-message">{n.message}</p>
                <span className="my-support-item-time">
                  {formatTime(n.timestamp)}
                </span>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Crisis Support Records (fetched from backend)
// ---------------------------------------------------------------------------

interface CrisisRecordsSectionProps {
  userId: string;
}

function CrisisRecordsSection({ userId }: CrisisRecordsSectionProps) {
  const [records, setRecords] = useState<CrisisAlertRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchRecords = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const url = `/api/crisis/alerts/${encodeURIComponent(userId)}`;
      console.log("[CrisisRecords] GET", url, new Error().stack);
      console.log("[CrisisRecords] userId prop:", userId);
      const res = await fetch(url);
      console.log("[CrisisRecords] HTTP status:", res.status);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data: CrisisAlertRecord[] = await res.json();
      console.log("[CrisisRecords] response JSON:", data);
      setRecords(data);
    } catch (err) {
      console.error("[CrisisRecords] fetch failed:", err);
      setError("Unable to load crisis records.");
    } finally {
      setLoading(false);
    }
  }, [userId]);

  // Fetch on mount
  useEffect(() => {
    fetchRecords();
  }, [fetchRecords]);

  return (
    <div className="crisis-records-section">
      {/* Section header + refresh */}
      <div className="crisis-records-header">
        <h3 className="my-support-section-title" style={{ marginBottom: 0 }}>
          Crisis Support Records
        </h3>
        <button
          type="button"
          className="crisis-records-refresh-btn"
          onClick={fetchRecords}
          disabled={loading}
          title="Refresh"
          aria-label="Refresh crisis records"
        >
          <RefreshCw
            size={14}
            className={loading ? "spin" : ""}
          />
        </button>
      </div>

      {loading && records.length === 0 && (
        <p className="crisis-records-loading">Loading...</p>
      )}

      {error && (
        <p className="crisis-records-error">{error}</p>
      )}

      {!loading && !error && records.length === 0 && (
        <div className="crisis-records-empty">
          <p className="crisis-records-empty-text">
            No crisis alerts on record.
          </p>
        </div>
      )}

      {records.length > 0 && (
        <ul className="crisis-records-list">
          {records.map((record) => (
            <li key={record.id} className="crisis-record-card">
              {/* Orange warning icon */}
              <span className="crisis-record-icon" aria-hidden="true">
                <AlertTriangle size={18} color="#f97316" strokeWidth={2} />
              </span>

              {/* Body */}
              <div className="crisis-record-body">
                <span className="crisis-record-title">Counselor Notified</span>

                <span className="crisis-record-source">
                  {record.source === "chat"
                    ? "Source: Chat"
                    : "Source: Diary"}
                </span>

                <span className="crisis-record-time">
                  {formatCrisisTime(record.triggered_at)}
                </span>

                {/* Status badge — always "Resolved" in demo/mock mode */}
                <span className="crisis-record-status-badge">Resolved</span>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

interface MySupportProps {
  userId?: string;
}

export default function MySupport({ userId = "" }: MySupportProps) {
  return (
    <div className="my-support-page">
      {/* Page header */}
      <div className="my-support-header">
        <div className="my-support-header__left">
          <HeartHandshake size={20} />
          <h1>My Support</h1>
        </div>
        <SimulateButton />
      </div>

      {/* Supporter card */}
      <SupporterCard />

      {/* Notification history */}
      <NotificationSection />

      {/* Crisis Support Records */}
      <CrisisRecordsSection userId={userId} />
    </div>
  );
}
