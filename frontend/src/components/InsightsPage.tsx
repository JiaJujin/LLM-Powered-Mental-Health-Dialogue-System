import { useMemo, useState } from "react";
import {
  CalendarDays,
  Flame,
  Heart,
  Sparkles,
  TrendingUp,
  MessageCircle,
  Quote
} from "lucide-react";
import { fetchInsights } from "../api";
import type { InsightsResponse } from "../types";
import StatCard from "./StatCard";
import MoodChartCard from "./MoodChartCard";
import HumanSupportCard from "./HumanSupportCard";
import AnalysisHistoryCard from "./AnalysisHistoryCard";
import InsightSectionCard from "./InsightSectionCard";

interface Props {
  anonId: string;
}

export default function InsightsPage({ anonId }: Props) {
  const [data, setData] = useState<InsightsResponse | null>(null);
  const [loading, setLoading] = useState(false);

  const loadInsights = async () => {
    setLoading(true);
    try {
      const result = await fetchInsights({ anon_id: anonId });
      setData(result);
    } catch (error) {
      alert("加载 Insights 失败");
    } finally {
      setLoading(false);
    }
  };

  const chartData = useMemo(() => {
    if (!data) return [];
    return Object.entries(data.emotion_distribution || {}).map(([name, value]) => ({
      name,
      value
    }));
  }, [data]);

  const hasRisk = !!data?.risk_distribution && (
    (data.risk_distribution["Level 2"] ?? 0) > 0 ||
    (data.risk_distribution["Level 3"] ?? 0) > 0
  );

  return (
    <div className="page insights-page">
      <div className="page-header">
        <h1>Mental Health Insights</h1>
        <p>Comprehensive analysis of your journal entries and survey responses</p>
      </div>

      <div className="top-actions">
        <button className="dark-btn" onClick={loadInsights}>
          {loading ? "Generating..." : "Generate New Analysis"}
        </button>
      </div>

      {!data && (
        <div className="empty-card">
          <p>点击 Generate New Analysis 生成最近 14 天的 AI 洞察。</p>
        </div>
      )}

      {data && (
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
              </div>

              <p className="hero-analysis-text">{data.llm_summary}</p>
            </div>

            <AnalysisHistoryCard items={data.analysis_history || []} />
          </div>

          <div className="sections-grid">
            <InsightSectionCard
              title="Emotional Patterns"
              icon={<TrendingUp size={18} />}
              content={data.emotional_patterns}
            />
            <InsightSectionCard
              title="Common Themes"
              icon={<MessageCircle size={18} />}
              content={data.common_themes}
            />
            <InsightSectionCard
              title="Growth Observations"
              icon={<Sparkles size={18} />}
              content={data.growth_observations}
            />
            <InsightSectionCard
              title="Recommendations"
              icon={<Heart size={18} />}
              content={data.recommendations}
            />
          </div>

          {data.affirmation && (
            <div className="card affirmation-card">
              <div className="card-title with-icon">
                <Quote size={20} />
                <span>Affirmation / 鼓励语</span>
              </div>
              <p className="affirmation-text">{data.affirmation}</p>
            </div>
          )}

          {data.focus_points?.length > 0 && (
            <div className="card">
              <div className="card-title">Focus Points</div>
              <ul className="focus-list">
                {data.focus_points.map((point, idx) => (
                  <li key={idx}>{point}</li>
                ))}
              </ul>
            </div>
          )}

          {data.timeline?.length > 0 && (
            <div className="card">
              <div className="card-title">Recent Timeline</div>
              <div className="timeline-list">
                {data.timeline.map((item, idx) => (
                  <div key={idx} className="timeline-item">
                    <div className="timeline-top">
                      <span className="timeline-date">{item.date}</span>
                      <span className="timeline-meta">
                        {item.emotion_label || "Unknown"} · Risk {item.risk_level ?? "N/A"}
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
