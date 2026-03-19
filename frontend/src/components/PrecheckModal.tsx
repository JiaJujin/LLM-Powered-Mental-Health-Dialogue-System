import { useState } from "react";
import { X } from "lucide-react";
import { submitPrecheck } from "../api";
import type { PrecheckRequest, PrecheckResponse } from "../types";

interface Props {
  anonId: string;
  onComplete: (result: PrecheckResponse) => void;
  onSkip: () => void;
  isOpen: boolean;
  onClose: () => void;
}

const BODY_FEELINGS = [
  "Tense",
  "Tired", 
  "Restless",
  "Calm",
  "Heavy"
];

const NEEDS = [
  "Validation",
  "Clarity", 
  "Companionship",
  "Reflection"
];

const EMOTIONS = [
  "Sad",
  "Anxious",
  "Angry",
  "Numb",
  "Overwhelmed",
  "Okay"
];

export default function PrecheckModal({
  anonId,
  onComplete,
  onSkip,
  isOpen,
  onClose
}: Props) {
  const [bodyFeeling, setBodyFeeling] = useState("");
  const [need, setNeed] = useState("");
  const [emotion, setEmotion] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  if (!isOpen) return null;

  const handleSubmit = async () => {
    if (!bodyFeeling || !need || !emotion) {
      setError("Please select an option for each category.");
      return;
    }

    setLoading(true);
    setError("");

    try {
      const result = await submitPrecheck({
        anon_id: anonId,
        body_feeling: bodyFeeling,
        need: need,
        emotion: emotion
      } as PrecheckRequest);
      onComplete(result);
      onClose();
    } catch (err) {
      console.error("Precheck failed:", err);
      setError("Something went wrong. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleSkip = () => {
    onSkip();
    onClose();
  };

  const isSelected = (value: string, current: string) => 
    value === current ? "selected" : "";

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="precheck-modal" onClick={e => e.stopPropagation()}>
        <button className="modal-close" onClick={handleSkip}>
          <X size={20} />
        </button>

        <div className="modal-header">
          <h2>How are you arriving today?</h2>
          <p className="modal-subtitle">
            A quick check-in helps the AI support you more gently.
          </p>
        </div>

        <div className="modal-body">
          {/* Body Feeling */}
          <div className="precheck-section">
            <label>How does your body feel?</label>
            <div className="chip-group">
              {BODY_FEELINGS.map(item => (
                <button
                  key={item}
                  className={`chip ${isSelected(item, bodyFeeling)}`}
                  onClick={() => setBodyFeeling(item)}
                >
                  {item}
                </button>
              ))}
            </div>
          </div>

          {/* Need */}
          <div className="precheck-section">
            <label>What do you need right now?</label>
            <div className="chip-group">
              {NEEDS.map(item => (
                <button
                  key={item}
                  className={`chip ${isSelected(item, need)}`}
                  onClick={() => setNeed(item)}
                >
                  {item}
                </button>
              ))}
            </div>
          </div>

          {/* Emotion */}
          <div className="precheck-section">
            <label>How are you feeling emotionally?</label>
            <div className="chip-group">
              {EMOTIONS.map(item => (
                <button
                  key={item}
                  className={`chip ${isSelected(item, emotion)}`}
                  onClick={() => setEmotion(item)}
                >
                  {item}
                </button>
              ))}
            </div>
          </div>

          {error && <div className="precheck-error">{error}</div>}
        </div>

        <div className="modal-footer">
          <button className="btn-skip" onClick={handleSkip}>
            Skip for now
          </button>
          <button 
            className="btn-primary" 
            onClick={handleSubmit}
            disabled={loading || !bodyFeeling || !need || !emotion}
          >
            {loading ? "Continuing..." : "Continue"}
          </button>
        </div>
      </div>
    </div>
  );
}
