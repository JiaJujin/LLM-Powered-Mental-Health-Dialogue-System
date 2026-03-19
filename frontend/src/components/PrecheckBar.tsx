import { useState } from "react";
import { Heart, X } from "lucide-react";
import type { PrecheckResponse } from "../types";

interface Props {
  precheckResult: PrecheckResponse | null;
  onSubmit: (payload: { body_feeling: string; need: string; emotion: string }) => void;
}

export default function PrecheckBar({ precheckResult, onSubmit }: Props) {
  const [isOpen, setIsOpen] = useState(!precheckResult);
  const [bodyFeeling, setBodyFeeling] = useState("");
  const [need, setNeed] = useState("");
  const [emotion, setEmotion] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!bodyFeeling || !need || !emotion) return;

    setLoading(true);
    try {
      await onSubmit({ body_feeling: bodyFeeling, need, emotion });
      setIsOpen(false);
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen && precheckResult) {
    return (
      <div className="precheck-bar">
        <div className="precheck-result">
          <Heart size={16} />
          <span>Current mode: <strong>{precheckResult.role}</strong></span>
          <button className="precheck-update-btn" onClick={() => setIsOpen(true)}>
            Update
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="precheck-bar">
      <div className="precheck-card">
        <div className="precheck-header">
          <h3>How are you feeling right now?</h3>
          {precheckResult && (
            <button className="precheck-close" onClick={() => setIsOpen(false)}>
              <X size={18} />
            </button>
          )}
        </div>

        <form onSubmit={handleSubmit}>
          <div className="precheck-inputs">
            <div className="input-group">
              <label>Body Feeling</label>
              <input
                type="text"
                value={bodyFeeling}
                onChange={(e) => setBodyFeeling(e.target.value)}
                placeholder="e.g., tired, relaxed, tense..."
              />
            </div>

            <div className="input-group">
              <label>Need</label>
              <input
                type="text"
                value={need}
                onChange={(e) => setNeed(e.target.value)}
                placeholder="e.g., talk, listen, vent..."
              />
            </div>

            <div className="input-group">
              <label>Emotion</label>
              <input
                type="text"
                value={emotion}
                onChange={(e) => setEmotion(e.target.value)}
                placeholder="e.g., happy, sad, anxious..."
              />
            </div>
          </div>

          <button type="submit" className="precheck-submit" disabled={loading}>
            {loading ? "Saving..." : "Continue"}
          </button>
        </form>
      </div>
    </div>
  );
}
