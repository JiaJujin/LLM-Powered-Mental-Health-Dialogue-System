import { useState } from "react";
import { submitJournal } from "../api";
import type { JournalResponse, PrecheckResponse } from "../types";
import ConversationView from "./ConversationView";
import JournalForm from "./JournalForm";

interface Props {
  anonId: string;
  precheckResult: PrecheckResponse | null;
  onSubmitted: (result: JournalResponse) => void;
  lastJournalResult: JournalResponse | null;
  goToCheckin: () => void;
}

export default function JournalPage({
  anonId,
  precheckResult,
  onSubmitted,
  lastJournalResult,
  goToCheckin
}: Props) {
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (payload: {
    content: string;
    mood?: string;
    weather?: string;
  }) => {
    setLoading(true);
    try {
      const data = await submitJournal({
        anon_id: anonId,
        content: payload.content,
        mood: payload.mood,
        weather: payload.weather
      });

      onSubmitted(data);
    } catch (error) {
      alert("提交日记失败");
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  if (!precheckResult) {
    return (
      <div className="page">
        <div className="page-header">
          <h1>Journal</h1>
          <p>You need a check-in before journaling.</p>
        </div>

        <div className="empty-card">
          <p>请先完成 Pre-check，再开始记录日记。</p>
          <button className="primary-btn" onClick={goToCheckin}>
            Go to Check-in
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="page">
      <div className="page-header">
        <h1>Journal</h1>
        <p>Your assigned role: {precheckResult.role}</p>
      </div>

      <JournalForm onSubmit={handleSubmit} loading={loading} />

      {lastJournalResult && (
        <ConversationView data={lastJournalResult} />
      )}
    </div>
  );
}
