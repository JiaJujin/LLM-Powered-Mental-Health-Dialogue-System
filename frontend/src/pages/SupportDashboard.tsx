/**
 * Support Dashboard — Crisis Alert Management Page
 *
 * Displays all LLM-classified crisis alerts with filtering, mark-as-read,
 * and a demo simulation button for teacher demos.
 */

import { useState } from "react";
import { ShieldAlert, BookOpen, MessageSquare, Clock, AlertTriangle } from "lucide-react";
import { useAlertStore, alertStore } from "../utils/alertStore";
import type { CrisisAlert, CrisisLevel } from "../utils/crisisTypes";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatTimestamp(iso: string): string {
  try {
    const d = new Date(iso);
    const pad = (n: number) => String(n).padStart(2, "0");
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
  } catch {
    return iso;
  }
}

const LEVEL_META: Record<CrisisLevel, { color: string; label: string }> = {
  none:    { color: "#9ca3af", label: "None" },
  low:      { color: "#eab308", label: "Low" },
  medium:   { color: "#f97316", label: "Medium" },
  high:     { color: "#ef4444", label: "High" },
};

function LevelBadge({ level }: { level: CrisisLevel }) {
  const { color, label } = LEVEL_META[level] ?? LEVEL_META.low;
  return (
    <span
      className="crisis-level-badge"
      style={{ background: color, color: "#fff", fontSize: 11, padding: "2px 8px", borderRadius: 12, fontWeight: 700 }}
    >
      {label}
    </span>
  );
}

function SourceIcon({ source }: { source: "diary" | "chatbot" }) {
  return source === "diary" ? (
    <span title="Diary"><BookOpen size={13} /></span>
  ) : (
    <span title="Chatbot"><MessageSquare size={13} /></span>
  );
}

// ---------------------------------------------------------------------------
// Alert Card
// ---------------------------------------------------------------------------

function AlertCard({ alert }: { alert: CrisisAlert }) {
  const { markAsRead } = useAlertStore();
  const meta = LEVEL_META[alert.level] ?? LEVEL_META.low;

  return (
    <div className={`crisis-card crisis-card--${alert.level} ${alert.isRead ? "crisis-card--read" : ""}`}>
      {/* Left colour bar */}
      <div
        className="crisis-card__bar"
        style={{ background: meta.color }}
      />

      <div className="crisis-card__body">
        {/* Header row */}
        <div className="crisis-card__header">
          <LevelBadge level={alert.level} />
          {alert.level === "high" && (
            <span className="crisis-card__pulse" style={{ color: "#ef4444" }}>
              ●
            </span>
          )}
          <span className="crisis-card__source">
            <SourceIcon source={alert.source} />
            {alert.source === "diary" ? " Diary" : " Chatbot"}
          </span>
          <span className="crisis-card__user" title="Anonymous user ID">
            {alert.userId}
          </span>
          {!alert.isRead && (
            <span className="crisis-card__new-badge">NEW</span>
          )}
        </div>

        {/* Timestamp */}
        <div className="crisis-card__time">
          <Clock size={12} />
          {formatTimestamp(alert.timestamp)}
        </div>

        {/* Text snippet */}
        <blockquote className="crisis-card__snippet">
          {alert.textSnippet}
        </blockquote>

        {/* LLM reasoning */}
        {alert.reasoning && (
          <p className="crisis-card__reasoning">
            <AlertTriangle size={12} />
            {alert.reasoning}
          </p>
        )}

        {/* Theme tags */}
        {alert.matchedThemes.length > 0 && (
          <div className="crisis-card__tags">
            {alert.matchedThemes.map((t) => (
              <span key={t} className="crisis-tag">{t}</span>
            ))}
          </div>
        )}

        {/* Footer */}
        <div className="crisis-card__footer">
          {!alert.isRead && (
            <button
              className="crisis-card__mark-read"
              onClick={() => markAsRead(alert.id)}
            >
              Mark as read
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Empty State
// ---------------------------------------------------------------------------

function EmptyState() {
  return (
    <div className="crisis-empty">
      <ShieldAlert size={48} strokeWidth={1} style={{ color: "#d1d5db" }} />
      <p>No alerts yet.</p>
      <p className="crisis-empty__sub">
        Alerts will appear here when crisis signals are detected.
      </p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Filter definitions
// ---------------------------------------------------------------------------

type Filter = "all" | "unread" | CrisisLevel;

const FILTERS: { key: Filter; label: string }[] = [
  { key: "all",     label: "All" },
  { key: "unread",  label: "Unread" },
  { key: "low",     label: "Low" },
  { key: "medium",  label: "Medium" },
  { key: "high",    label: "High" },
];

// ---------------------------------------------------------------------------
// Simulate Alert — for teacher demo only
// ---------------------------------------------------------------------------

function SimulateButton() {
  const simulate = () => {
    const fakeAlert: CrisisAlert = {
      id: crypto.randomUUID(),
      timestamp: new Date().toISOString(),
      source: Math.random() > 0.5 ? "diary" : "chatbot",
      userId: `User #${Math.floor(1000 + Math.random() * 9000)}`,
      textSnippet:
        "我觉得大家没有我会更好，最近真的很累了，不想再撑下去了...",
      matchedThemes: [
        "hopelessness",
        "burden to others",
        "suicidal ideation",
      ],
      reasoning: "表达强烈绝望感及对生命的放弃意念",
      level: (["low", "medium", "high"] as Exclude<CrisisLevel, "none">[])[
        Math.floor(Math.random() * 3)
      ],
      isRead: false,
    };
    alertStore.addAlert(fakeAlert);
  };

  return (
    <button
      type="button"
      onClick={simulate}
      className="crisis-simulate-btn"
      title="Demo only — generates a fake alert"
    >
      🧪 Simulate Alert
    </button>
  );
}

// ---------------------------------------------------------------------------
// Main Dashboard
// ---------------------------------------------------------------------------

export default function SupportDashboard() {
  const { alerts, unreadCount, markAllAsRead } = useAlertStore();
  const [filter, setFilter] = useState<Filter>("all");

  const filtered =
    filter === "all"
      ? alerts
      : filter === "unread"
      ? alerts.filter((a) => !a.isRead)
      : alerts.filter((a) => a.level === filter);

  return (
    <div className="support-dashboard">
      {/* Page header */}
      <div className="support-header">
        <div className="support-header__left">
          <ShieldAlert size={20} />
          <h1>Support Dashboard</h1>
          {unreadCount > 0 && (
            <span className="support-header__badge">{unreadCount}</span>
          )}
        </div>
        <SimulateButton />
      </div>

      {/* Filter bar */}
      <div className="support-filters">
        {FILTERS.map((f) => (
          <button
            key={f.key}
            type="button"
            className={`support-filter-btn ${filter === f.key ? "active" : ""}`}
            onClick={() => setFilter(f.key)}
          >
            {f.label}
            {f.key === "unread" && unreadCount > 0 && (
              <span className="support-filter-count">{unreadCount}</span>
            )}
          </button>
        ))}

        {unreadCount > 0 && (
          <button
            type="button"
            className="support-mark-all-btn"
            onClick={markAllAsRead}
          >
            Mark all as read
          </button>
        )}
      </div>

      {/* Alert list */}
      {filtered.length === 0 ? (
        <EmptyState />
      ) : (
        <div className="crisis-list">
          {filtered.map((alert) => (
            <AlertCard key={alert.id} alert={alert} />
          ))}
        </div>
      )}
    </div>
  );
}
