// frontend/src/components/InsightsView.tsx
import React, { useState } from "react";
import axios from "axios";
import {
  CalendarDays,
  Flame,
  Heart,
  Sparkles,
  TrendingUp,
  MessageCircle,
  BadgeHelp,
  History,
} from "lucide-react";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from "recharts";

interface Props {
  anonId: string;
}

const cardClass =
  "bg-white rounded-2xl border border-neutral-200 shadow-sm p-6";

const InsightsView: React.FC<Props> = ({ anonId }) => {
  const [data, setData] = useState<any | null>(null);
  const [loading, setLoading] = useState(false);

  const loadInsights = async () => {
    setLoading(true);
    try {
      const res = await axios.post("http://localhost:8000/api/insights", {
        anon_id: anonId,
      });
      setData(res.data);
    } catch (err) {
      console.error(err);
      alert("加载 Insights 失败");
    } finally {
      setLoading(false);
    }
  };

  const chartData = data
    ? Object.entries(data.emotion_distribution || {}).map(([name, value]) => ({
        name,
        value,
      }))
    : [];

  const hasHighRisk =
    data?.risk_distribution &&
    ((data.risk_distribution["Level 2"] ?? 0) > 0 ||
      (data.risk_distribution["Level 3"] ?? 0) > 0);

  return (
    <div className="min-h-screen bg-neutral-50 p-6 md:p-10">
      <div className="max-w-7xl mx-auto space-y-6">
        <div className="space-y-2">
          <h1 className="text-4xl font-bold tracking-tight">
            Mental Health Insights
          </h1>
          <p className="text-neutral-500">
            Comprehensive analysis of your recent 14-day journal entries
          </p>
        </div>

        <div className="flex justify-end">
          <button
            onClick={loadInsights}
            className="px-5 py-2.5 rounded-xl bg-black text-white hover:bg-neutral-800 transition"
          >
            {loading ? "Generating..." : "Generate New Analysis"}
          </button>
        </div>

        {!data && (
          <div className={`${cardClass} text-neutral-500`}>
            Click “Generate New Analysis” to load your recent 14-day insights.
          </div>
        )}

        {data && (
          <>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
              <div className={cardClass}>
                <div className="flex items-center gap-2 text-neutral-500 text-sm mb-3">
                  <CalendarDays size={16} />
                  <span>Total Entries</span>
                </div>
                <div className="text-5xl font-bold">{data.total_entries}</div>
              </div>

              <div className={cardClass}>
                <div className="flex items-center gap-2 text-neutral-500 text-sm mb-3">
                  <Flame size={16} />
                  <span>Current Streak</span>
                </div>
                <div className="text-5xl font-bold">
                  {data.current_streak || 0}
                </div>
              </div>

              <div className={cardClass}>
                <div className="flex items-center gap-2 text-neutral-500 text-sm mb-3">
                  <Heart size={16} />
                  <span>Top Mood</span>
                </div>
                <div className="text-3xl font-bold">
                  {data.top_mood || "Unknown"}
                </div>
              </div>
            </div>

            <div className={cardClass}>
              <h2 className="text-xl font-semibold mb-6">Mood Distribution</h2>
              <div className="h-80">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} />
                    <XAxis dataKey="name" />
                    <YAxis allowDecimals={false} />
                    <Tooltip />
                    <Bar dataKey="value" fill="#1f1a17" radius={[8, 8, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div
              className={`${cardClass} ${
                hasHighRisk ? "border-amber-300 bg-amber-50" : ""
              }`}
            >
              <div className="flex items-center gap-2 mb-3 font-semibold">
                <BadgeHelp size={18} />
                <span>Need Human Support?</span>
              </div>
              <p className="text-neutral-600 mb-4">
                While AI insights are helpful, sometimes talking to a real person
                makes all the difference. Connect with counsellors, social workers,
                writers, and peer supporters who are here to help.
              </p>
              <button className="px-4 py-2 rounded-xl bg-black text-white hover:bg-neutral-800 transition">
                Connect with Helpers
              </button>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <div
                className={`${cardClass} lg:col-span-2 flex flex-col justify-center min-h-[220px]`}
              >
                <div className="flex items-center gap-2 mb-4">
                  <Sparkles size={20} />
                  <h2 className="text-2xl font-semibold">Personal Analysis</h2>
                </div>
                <p className="text-neutral-600 leading-7 whitespace-pre-wrap">
                  {data.llm_summary}
                </p>
              </div>

              <div className={cardClass}>
                <div className="flex items-center gap-2 mb-4">
                  <History size={18} />
                  <h2 className="text-xl font-semibold">Analysis History</h2>
                </div>
                <div className="space-y-3">
                  {(data.analysis_history || []).length > 0 ? (
                    data.analysis_history.map((item: string, idx: number) => (
                      <div
                        key={idx}
                        className={`px-3 py-2 rounded-xl border ${
                          idx === 0
                            ? "bg-black text-white border-black"
                            : "bg-white text-neutral-800 border-neutral-200"
                        }`}
                      >
                        {item}
                      </div>
                    ))
                  ) : (
                    <div className="text-sm text-neutral-500">
                      No previous analysis history yet
                    </div>
                  )}
                </div>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-6">
              <div className={`${cardClass} min-h-[260px]`}>
                <div className="flex items-center gap-2 mb-4">
                  <TrendingUp size={18} />
                  <h3 className="text-lg font-semibold">Emotional Patterns</h3>
                </div>
                <p className="text-neutral-700 leading-7">
                  {data.emotional_patterns || "暂无分析内容"}
                </p>
              </div>

              <div className={`${cardClass} min-h-[260px]`}>
                <div className="flex items-center gap-2 mb-4">
                  <MessageCircle size={18} />
                  <h3 className="text-lg font-semibold">Common Themes</h3>
                </div>
                <p className="text-neutral-700 leading-7">
                  {data.common_themes || "暂无分析内容"}
                </p>
              </div>

              <div className={`${cardClass} min-h-[260px]`}>
                <div className="flex items-center gap-2 mb-4">
                  <Sparkles size={18} />
                  <h3 className="text-lg font-semibold">Growth Observations</h3>
                </div>
                <p className="text-neutral-700 leading-7">
                  {data.growth_observations || "暂无分析内容"}
                </p>
              </div>

              <div className={`${cardClass} min-h-[260px]`}>
                <div className="flex items-center gap-2 mb-4">
                  <Heart size={18} />
                  <h3 className="text-lg font-semibold">Recommendations</h3>
                </div>
                <p className="text-neutral-700 leading-7">
                  {data.recommendations || "暂无分析内容"}
                </p>
              </div>
            </div>

            {data.focus_points && data.focus_points.length > 0 && (
              <div className={cardClass}>
                <h2 className="text-xl font-semibold mb-4">Focus Points</h2>
                <ul className="list-disc pl-6 space-y-2 text-neutral-700">
                  {data.focus_points.map((item: string, idx: number) => (
                    <li key={idx}>{item}</li>
                  ))}
                </ul>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
};

export default InsightsView;
