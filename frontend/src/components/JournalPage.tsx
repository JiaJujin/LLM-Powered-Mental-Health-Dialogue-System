import { useState } from "react";
import { submitJournal } from "../api";
import type { JournalResponse, PrecheckResponse, JournalSubmitParams } from "../types";
import { formatRoleName } from "../utils";
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
      alert("Failed to submit journal.");
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmitWithMeta = async (payload: JournalSubmitParams) => {
    setLoading(true);
    try {
      const data = await submitJournal({
        anon_id: anonId,
        content: payload.content,
        mood: payload.mood,
        weather: payload.weather,
        title: payload.title,
        entry_date: payload.entry_date,
        source_type: payload.source_type,
        original_input_text: payload.original_input_text,
        source_file_path: payload.source_file_path,
        input_metadata: payload.input_metadata,
      });

      onSubmitted(data);
    } catch (error) {
      alert("Failed to submit journal.");
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
          <p>Please complete the Pre-check before you can start journaling.</p>
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
        <p>Your assigned role: {precheckResult ? formatRoleName(precheckResult.role) : "General Support"}</p>
      </div>

      <JournalForm onSubmit={handleSubmit} onSubmitWithMeta={handleSubmitWithMeta} loading={loading} />

      {lastJournalResult && (
        <ConversationView data={lastJournalResult} />
      )}
    </div>
  );
}
