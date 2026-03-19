import { useState } from "react";

interface Props {
  onSubmit: (payload: {
    body_feeling: string;
    need: string;
    emotion: string;
  }) => Promise<void> | void;
  loading?: boolean;
}

const BODY_OPTIONS = ["Tense", "Tired", "Restless", "Calm", "Heavy"];
const NEED_OPTIONS = ["Validation", "Clarity", "Companionship", "Reflection"];
const EMOTION_OPTIONS = ["Sad", "Anxious", "Angry", "Numb", "Overwhelmed", "Okay"];

export default function PrecheckForm({ onSubmit, loading = false }: Props) {
  const [bodyFeeling, setBodyFeeling] = useState("Tense");
  const [need, setNeed] = useState("Validation");
  const [emotion, setEmotion] = useState("Sad");

  const handleSubmit = async () => {
    await onSubmit({
      body_feeling: bodyFeeling,
      need,
      emotion
    });
  };

  return (
    <div className="form-card">
      <div className="form-grid">
        <div className="field">
          <label>Body feeling</label>
          <select
            value={bodyFeeling}
            onChange={(e) => setBodyFeeling(e.target.value)}
          >
            {BODY_OPTIONS.map((item) => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
          </select>
        </div>

        <div className="field">
          <label>Need</label>
          <select value={need} onChange={(e) => setNeed(e.target.value)}>
            {NEED_OPTIONS.map((item) => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
          </select>
        </div>

        <div className="field">
          <label>Emotion</label>
          <select value={emotion} onChange={(e) => setEmotion(e.target.value)}>
            {EMOTION_OPTIONS.map((item) => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
          </select>
        </div>
      </div>

      <button className="primary-btn" onClick={handleSubmit} disabled={loading}>
        {loading ? "Submitting..." : "Start Check-in"}
      </button>
    </div>
  );
}
