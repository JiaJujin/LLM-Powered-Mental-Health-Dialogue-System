import { useMemo, useState, useEffect, useRef } from "react";
import {
  CalendarDays,
  Flame,
  Heart,
  Sparkles,
  TrendingUp,
  MessageCircle,
  Quote,
  AlertCircle,
  BarChart3,
  Loader2,
} from "lucide-react";
import {
  fetchCachedInsights,
  fetchCachedAnalysis,
  fetchInsights,
  fetchAnalysisByDate,
} from "../api";
import type { InsightsResponse } from "../types";
import StatCard from "./StatCard";
import MoodChartCard from "./MoodChartCard";
import HumanSupportCard from "./HumanSupportCard";
import AnalysisHistoryCard from "./AnalysisHistoryCard";
import InsightSectionCard from "./InsightSectionCard";
import {
  getInsightsCache,
  setInsightsCache,
} from "../lib/insightsCache";

interface Props {
  anonId: string;
  onGoToWrite?: () => void;
}

// ──────────────────────────────────────────────────────────────────────────────
// State machine modes
// ──────────────────────────────────────────────────────────────────────────────
//
//  ready               : analysis data is available and displayed
//  generating          : user clicked "Generate New Analysis" — POST in flight
//                        old content stays visible throughout
//  refreshing          : background cache-stale refresh in progress (not from button)
//                        old content stays visible; "Updating…" shown top-right
//  empty               : backend confirmed user has no journal entries at all
//  initial_loading     : truly first visit, no memory/ session/ backend data at all
//
// ──────────────────────────────────────────────────────────────────────────────

type PageMode =
  | "initial_loading" // only when confirmed no data anywhere, ever
  | "empty"           // backend confirmed no entries in past 14 days
  | "ready"           // analysis visible, no background work
  | "refreshing"      // analysis visible, background POST refreshing it
  | "generating";     // analysis visible, user-triggered POST running

// ──────────────────────────────────────────────────────────────────────────────
// Guarded uiMode setter — NEVER allows reverting to initial_loading / empty
// when we already have renderable analysis on screen.
// ──────────────────────────────────────────────────────────────────────────────

function useInsightsUiMode(
  initialMode: PageMode,
  hasData: () => boolean
): [PageMode, (next: PageMode, reason: string) => void] {
  // Sync initial state from sessionStorage so first render is correct
  const sessionHadData =
    typeof window !== "undefined" &&
    sessionStorage.getItem("mj_insights_ever_had_data") === "1";

  const [mode, rawSetMode] = useState<PageMode>(() =>
    sessionHadData ? "ready" : initialMode
  );

  function setMode(next: PageMode, reason: string) {
    const BLOCKED =
      (next === "initial_loading" || next === "empty") && hasData();
    if (BLOCKED) {
      console.error(
        `[ANALYSIS_UI][GUARD] BLOCKED illegal transition ${mode} → ${next}` +
          ` reason="${reason}" — hasData=true, staying at ${mode}`
      );
      return;
    }
    if (mode !== next) {
      console.log(
        `[ANALYSIS_UI] mode ${mode} → ${next}  reason="${reason}"`
      );
    }
    rawSetMode(next);
  }

  return [mode, setMode];
}

// ──────────────────────────────────────────────────────────────────────────────
// Session-storage backed analysis cache (survives component re-mounts)
// ──────────────────────────────────────────────────────────────────────────────

const SESSION_KEY = "mj_insights_session";

interface SessionCache {
  analysis: InsightsResponse;
  updatedAt: number;
}

function readSessionCache(): InsightsResponse | null {
  try {
    const raw = sessionStorage.getItem(SESSION_KEY);
    if (!raw) return null;
    const parsed: SessionCache = JSON.parse(raw);
    return parsed.analysis ?? null;
  } catch {
    return null;
  }
}

function writeSessionCache(analysis: InsightsResponse) {
  try {
    sessionStorage.setItem(
      SESSION_KEY,
      JSON.stringify({ analysis, updatedAt: Date.now() } satisfies SessionCache)
    );
    sessionStorage.setItem("mj_insights_ever_had_data", "1");
  } catch {
    /* ignore quota errors */
  }
}

// ──────────────────────────────────────────────────────────────────────────────
// Guard: does this object have anything to render?
// ──────────────────────────────────────────────────────────────────────────────

function hasRenderableAnalysis(d: InsightsResponse | null): boolean {
  if (!d) return false;
  return !!(
    d.llm_summary ||
    d.emotional_patterns ||
    d.common_themes ||
    d.growth_observations ||
    d.recommendations ||
    d.affirmation ||
    (Array.isArray(d.focus_points) && d.focus_points.length > 0) ||
    (Array.isArray(d.timeline) && d.timeline.length > 0)
  );
}

// ──────────────────────────────────────────────────────────────────────────────
// Component
// ──────────────────────────────────────────────────────────────────────────────

export default function InsightsPage({ anonId, onGoToWrite }: Props) {
  // ── Primary data state ──────────────────────────────────────────────────────
  const [data, setData] = useState<InsightsResponse | null>(() =>
    readSessionCache()
  );

  // ── Page mode ──────────────────────────────────────────────────────────────
  const [mode, setMode] = useInsightsUiMode(
    "initial_loading",
    () => hasRenderableAnalysis(data)
  );

  // ── Manual generation in-flight ──────────────────────────────────────────────
  // Separate from `mode` so we can distinguish generating vs refreshing
  const [isManualGenerating, setIsManualGenerating] = useState(false);

  // ── Background refresh in-flight (prevents double-refresh) ───────────────────
  const isRefreshing = useRef(false);

  // ── Inline error banner (auto-clears after 4s) ──────────────────────────────
  const [inlineError, setInlineError] = useState<string | null>(null);

  // ── Historical analysis entry selected from history list ─────────────────────
  const [selectedEntry, setSelectedEntry] = useState<Record<string, unknown> | null>(
    null
  );

  // ── Derived: merge current data + selected historical entry ──────────────────
  const resolved = useMemo((): InsightsResponse | null => {
    if (!data) return null;
    if (!selectedEntry) return data;
    const s = selectedEntry as Record<string, unknown>;
    return {
      ...data,
      llm_summary: (s.llm_summary as string) || data.llm_summary || "",
      emotional_patterns:
        (s.emotional_patterns as string) || data.emotional_patterns || "",
      common_themes: (s.common_themes as string) || data.common_themes || "",
      growth_observations:
        (s.growth_observations as string) || data.growth_observations || "",
      recommendations:
        (s.recommendations as string) || data.recommendations || "",
      affirmation: (s.affirmation as string) || data.affirmation || "",
      focus_points:
        (s.focus_points as string[]) || data.focus_points || [],
    };
  }, [data, selectedEntry]);

  // ── Chart data ───────────────────────────────────────────────────────────────
  const chartData = useMemo(() => {
    if (!data) return [];
    return Object.entries(data.emotion_distribution || {}).map(
      ([name, value]) => ({ name, value })
    );
  }, [data]);

  const hasRisk =
    !!data?.risk_distribution &&
    ((data.risk_distribution["Level 2"] ?? 0) > 0 ||
      (data.risk_distribution["Level 3"] ?? 0) > 0);

  // ── Shared: update data + sessionStorage + mode helper ──────────────────────
  function commitAnalysis(result: InsightsResponse) {
    setData(result);
    setInsightsCache(anonId, result);
    writeSessionCache(result);
  }

  // ── Background refresh: stale cache check + optional POST ────────────────────
  async function backgroundRefresh() {
    if (isRefreshing.current) return;
    isRefreshing.current = true;

    console.log("[ANALYSIS_UI] backgroundRefresh START");

    try {
      const cacheStatus = await fetchCachedInsights(anonId);
      console.log("[ANALYSIS_UI] backgroundRefresh cacheStatus:", {
        has_cache: cacheStatus.has_cache,
        is_fresh: cacheStatus.is_fresh,
        source_entry_count: cacheStatus.source_entry_count,
      });

      // No entries at all
      if (!cacheStatus.has_cache && cacheStatus.source_entry_count === 0) {
        if (!hasRenderableAnalysis(data)) {
          setMode("empty", "no entries, no data");
        } else {
          console.log(
            "[ANALYSIS_UI] backgroundRefresh: no entries but we have stale data — keeping it"
          );
        }
        isRefreshing.current = false;
        return;
      }

      // Cache fresh → load full analysis
      if (cacheStatus.is_fresh) {
        try {
          const cached = await fetchCachedAnalysis(anonId);
          if (cached && hasRenderableAnalysis(cached)) {
            commitAnalysis(cached);
            setMode("ready", "cache fresh, analysis loaded");
          }
        } catch {
          console.warn("[ANALYSIS_UI] backgroundRefresh GET failed:", arguments);
        }
        isRefreshing.current = false;
        return;
      }

      // Cache stale → silent POST
      console.log("[ANALYSIS_UI] backgroundRefresh: cache stale, POST /insights");
      if (hasRenderableAnalysis(data)) {
        setMode("refreshing", "cache stale, content still visible");
      }
      try {
        const result = await fetchInsights({ anon_id: anonId });
        commitAnalysis(result);
        setMode("ready", "background refresh success");
        setInlineError(null);
      } catch (err) {
        console.warn("[ANALYSIS_UI] backgroundRefresh POST FAILED:", err);
        if (hasRenderableAnalysis(data)) {
          setInlineError("Update failed — showing last analysis.");
          setMode("ready", "background refresh failed, keep stale");
          setTimeout(() => setInlineError(null), 4000);
        }
      }
    } catch (err) {
      console.warn("[ANALYSIS_UI] backgroundRefresh outer FAILED:", err);
      if (hasRenderableAnalysis(data)) {
        setMode("ready", "background refresh outer failed, keep stale");
      }
    }

    isRefreshing.current = false;
  }

  // ── Manual "Generate New Analysis" ───────────────────────────────────────────
  async function handleGenerateClick() {
    const hadData = hasRenderableAnalysis(data);
    console.log(
      `[ANALYSIS_UI] Generate clicked — hadData=${hadData} — content WILL be preserved`
    );

    setInlineError(null);
    setIsManualGenerating(true);
    setSelectedEntry(null);
    // CRITICAL: setMode AFTER data check so guard above has correct snapshot
    setMode("generating", "user triggered manual generate");

    try {
      const result = await fetchInsights({ anon_id: anonId });
      console.log("[ANALYSIS_UI] Generate success:", {
        llm_summary_chars: result.llm_summary?.length,
      });
      commitAnalysis(result);
      setMode("ready", "manual generate success");
    } catch (err) {
      console.error("[ANALYSIS_UI] Generate FAILED:", err);
      if (!hasRenderableAnalysis(data)) {
        // This is the only scenario where blank is unavoidable (user had no data AND generation failed)
        console.error(
          "[ANALYSIS_UI] Generate failed AND had no data — unavoidable blank state"
        );
        setInlineError("Generation failed. Please try again.");
        setMode("initial_loading", "generate failed, no data");
      } else {
        // Had data: keep it, show gentle error
        setInlineError("Generation failed. Showing last analysis.");
        setMode("ready", "generate failed, keeping stale");
        setTimeout(() => setInlineError(null), 4000);
      }
    } finally {
      setIsManualGenerating(false);
    }
  }

  // ── Historical entry selection ───────────────────────────────────────────────
  async function handleHistorySelect(date: string) {
    console.log("[ANALYSIS_UI] historical entry selected:", date);
    try {
      const entry = await fetchAnalysisByDate(anonId, date);
      setSelectedEntry(entry);
    } catch {
      console.error("[ANALYSIS_UI] failed to fetch historical entry:", date);
    }
  }

  // ── Mount effect ─────────────────────────────────────────────────────────────
  useEffect(() => {
    // Session cache already loaded via useState initializer — show immediately
    if (data && hasRenderableAnalysis(data)) {
      console.log(
        "[ANALYSIS_UI] MOUNT: session cache hit — rendering immediately",
        { llm_summary_chars: data.llm_summary?.length }
      );
      setMode("ready", "session cache hit on mount");
      // Kick off background freshness check (non-blocking)
      backgroundRefresh();
      return;
    }

    // No session cache — must go to backend
    console.log("[ANALYSIS_UI] MOUNT: no session cache — querying backend");

    // Step 1: cache status
    fetchCachedInsights(anonId)
      .then(async (cacheStatus) => {
        console.log("[ANALYSIS_UI] MOUNT backend cacheStatus:", {
          has_cache: cacheStatus.has_cache,
          is_fresh: cacheStatus.is_fresh,
          source_entry_count: cacheStatus.source_entry_count,
        });

        // No entries anywhere
        if (
          !cacheStatus.has_cache &&
          cacheStatus.source_entry_count === 0
        ) {
          setMode("empty", "no entries on mount");
          return;
        }

        // Fetch full analysis
        const fullAnalysis = await fetchCachedAnalysis(anonId);
        if (!fullAnalysis) {
          // No analysis yet — trigger generation
          setMode("initial_loading", "no analysis on mount, generating...");
          try {
            const result = await fetchInsights({ anon_id: anonId });
            commitAnalysis(result);
            setMode("ready", "initial generation success");
          } catch (err) {
            console.error("[ANALYSIS_UI] initial generation FAILED:", err);
            // Only go to initial_loading if we truly have nothing
            if (!hasRenderableAnalysis(data)) {
              setMode("initial_loading", "initial generation failed");
            }
          }
          return;
        }

        // Got analysis from backend
        commitAnalysis(fullAnalysis);
        setMode(
          cacheStatus.is_fresh ? "ready" : "refreshing",
          cacheStatus.is_fresh
            ? "backend analysis loaded"
            : "backend analysis loaded, cache stale"
        );

        // If stale, refresh in background
        if (!cacheStatus.is_fresh) {
          backgroundRefresh();
        }
      })
      .catch((err) => {
        console.error("[ANALYSIS_UI] MOUNT backend FAILED:", err);
        // Backend unreachable: show whatever we have (session cache already tried)
        if (!hasRenderableAnalysis(data)) {
          setMode("initial_loading", "backend unreachable, no data");
          setInlineError("Failed to load insights. Please refresh.");
        } else {
          setMode("ready", "backend unreachable, keeping stale data");
        }
      });
  }, [anonId]); // intentionally run once on mount with stable anonId

  // ── Render helpers ───────────────────────────────────────────────────────────
  const showUpdating =
    (mode === "refreshing" || mode === "generating") && hasRenderableAnalysis(data);

  const showTopRightStatus = (() => {
    if (mode === "generating") return "Generating…";
    if (mode === "refreshing") return "Updating…";
    return null;
  })();

  const showSkeleton =
    (mode === "initial_loading" || mode === null) && !hasRenderableAnalysis(data);

  // ─────────────────────────────────────────────────────────────────────────────
  // RENDER
  // ─────────────────────────────────────────────────────────────────────────────
  return (
    <div className="page insights-page">
      {/* ── Header ─────────────────────────────────────────────────────────── */}
      <div className="page-header">
        <h1>Mental Health Insights</h1>
        <p>
          Comprehensive analysis of your journal entries and survey responses
        </p>
      </div>

      {/* ── Action bar ─────────────────────────────────────────────────────── */}
      <div className="top-actions">
        {/* Top-right status badge — only shown when content is visible */}
        {showTopRightStatus && (
          <span
            style={{
              fontSize: 12,
              color: "#a8a29e",
              marginRight: 12,
              display: "flex",
              alignItems: "center",
              gap: 5,
            }}
          >
            <Loader2
              size={11}
              style={{ animation: "spin 1s linear infinite" }}
            />
            {showTopRightStatus}
          </span>
        )}

        {/* Inline error */}
        {inlineError && (
          <span
            style={{
              fontSize: 12,
              color: "#f97316",
              marginRight: 8,
              display: "flex",
              alignItems: "center",
              gap: 4,
            }}
          >
            <AlertCircle size={11} />
            {inlineError}
          </span>
        )}

        <button
          className="dark-btn"
          onClick={handleGenerateClick}
          disabled={isManualGenerating}
        >
          {isManualGenerating ? (
            <>
              <Loader2
                size={14}
                style={{ animation: "spin 1s linear infinite", marginRight: 6 }}
              />
              Generating…
            </>
          ) : (
            "Generate New Analysis"
          )}
        </button>
      </div>

      {/* ── CASE 1: Skeleton (only when truly no data anywhere) ─────────────── */}
      {showSkeleton && (
        <div className="empty-card">
          <div className="spinner" />
          <p>Loading your insights…</p>
        </div>
      )}

      {/* ── CASE 2: No journal entries ─────────────────────────────────────── */}
      {mode === "empty" && !hasRenderableAnalysis(data) && (
        <div className="empty-card insights-empty">
          <BarChart3 size={56} className="insights-empty-icon" />
          <h2 className="insights-empty-title">No recent entries</h2>
          <p className="insights-empty-subtitle">
            Write a journal entry in the past 14 days to see your insights.
          </p>
          <button className="primary-btn" onClick={onGoToWrite}>
            Write an entry
          </button>
        </div>
      )}

      {/* ── CASE 3: Analysis content (ready OR refreshing OR generating) ─────── */}
      {/* The outer guard: if data is null, this entire block is skipped.        */}
      {/* If data is present, content renders regardless of mode.               */}
      {data && hasRenderableAnalysis(data) && (
        <>
          <div className="stats-grid">
            <StatCard
              icon={<CalendarDays size={16} />}
              label="Total Entries"
              value={data.total_entries}
            />
            <StatCard
              icon={<Flame size={16} />}
              label="Current Streak"
              value={data.current_streak}
            />
            <StatCard
              icon={<Heart size={16} />}
              label="Top Mood"
              value={data.top_mood || "Unknown"}
            />
          </div>

          <MoodChartCard data={chartData} />

          <HumanSupportCard highlighted={hasRisk} />

          <div className="analysis-grid">
            <div className="card hero-analysis">
              <div className="card-title with-icon">
                <Sparkles size={20} />
                <span>Personal Analysis</span>
                {selectedEntry && (
                  <span
                    style={{
                      fontSize: 12,
                      color: "#78716c",
                      marginLeft: 4,
                    }}
                  >
                    — viewing past analysis
                  </span>
                )}
              </div>
              <p className="hero-analysis-text">{resolved!.llm_summary}</p>
            </div>

            <AnalysisHistoryCard
              items={data.analysis_history || []}
              onSelect={handleHistorySelect}
            />
          </div>

          <div className="sections-grid">
            <InsightSectionCard
              title="Emotional Patterns"
              icon={<TrendingUp size={18} />}
              content={resolved!.emotional_patterns}
            />
            <InsightSectionCard
              title="Common Themes"
              icon={<MessageCircle size={18} />}
              content={resolved!.common_themes}
            />
            <InsightSectionCard
              title="Growth Observations"
              icon={<Sparkles size={18} />}
              content={resolved!.growth_observations}
            />
            <InsightSectionCard
              title="Recommendations"
              icon={<Heart size={18} />}
              content={resolved!.recommendations}
            />
          </div>

          {resolved!.affirmation && (
            <div className="card affirmation-card">
              <div className="card-title with-icon">
                <Quote size={20} />
                <span>Affirmation</span>
              </div>
              <p className="affirmation-text">{resolved!.affirmation}</p>
            </div>
          )}

          {Array.isArray(resolved!.focus_points) &&
            resolved!.focus_points.length > 0 && (
              <div className="card">
                <div className="card-title">Focus Points</div>
                <ul className="focus-list">
                  {resolved!.focus_points.map((point, idx) => (
                    <li key={idx}>{point}</li>
                  ))}
                </ul>
              </div>
            )}

          {Array.isArray(data.timeline) && data.timeline.length > 0 && (
            <div className="card">
              <div className="card-title">Recent Timeline</div>
              <div className="timeline-list">
                {data.timeline.map((item, idx) => (
                  <div key={idx} className="timeline-item">
                    <div className="timeline-top">
                      <span className="timeline-date">{item.date}</span>
                      <span className="timeline-meta">
                        {item.emotion_label || "Unknown"} · Risk{" "}
                        {item.risk_level ?? "N/A"}
                      </span>
                    </div>
                    <div className="timeline-summary">{item.summary}</div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
