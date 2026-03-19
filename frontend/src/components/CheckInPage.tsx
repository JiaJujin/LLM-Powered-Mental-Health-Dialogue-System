import { useState } from "react";
import { submitPrecheck } from "../api";
import type { PrecheckResponse } from "../types";
import PrecheckForm from "./PrecheckForm";

interface Props {
  anonId: string;
  onSuccess: (result: PrecheckResponse) => void;
}

export default function CheckInPage({ anonId, onSuccess }: Props) {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<PrecheckResponse | null>(null);

  const handleSubmit = async (payload: {
    body_feeling: string;
    need: string;
    emotion: string;
  }) => {
    setLoading(true);
    try {
      const data = await submitPrecheck({
        anon_id: anonId,
        body_feeling: payload.body_feeling,
        need: payload.need,
        emotion: payload.emotion
      });

      setResult(data);
      onSuccess(data);
    } catch (error) {
      alert("Pre-check 提交失败");
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page">
      <div className="page-header">
        <h1>Pre-check</h1>
        <p>Tell the system how you feel before journaling.</p>
      </div>

      <PrecheckForm onSubmit={handleSubmit} loading={loading} />

      {result && (
        <div className="result-card">
          <h3>Assigned role</h3>
          <div className="role-pill">{result.role}</div>
          <p className="muted">{result.reasons}</p>
          <p className="small-muted">
            Confidence: {result.confidence.toFixed(2)}
          </p>
        </div>
      )}
    </div>
  );
}
