import { useState } from "react";

interface Props {
  onSubmit: (payload: {
    content: string;
    mood?: string;
    weather?: string;
  }) => Promise<void> | void;
  loading?: boolean;
}

export default function JournalForm({ onSubmit, loading = false }: Props) {
  const [content, setContent] = useState("");
  const [mood, setMood] = useState("");
  const [weather, setWeather] = useState("");

  const handleSubmit = async () => {
    if (!content.trim()) {
      alert("请先写一点日记内容");
      return;
    }

    await onSubmit({
      content,
      mood,
      weather
    });
  };

  return (
    <div className="form-card">
      <div className="form-grid two">
        <div className="field">
          <label>Mood</label>
          <input
            value={mood}
            onChange={(e) => setMood(e.target.value)}
            placeholder="e.g. tired, calm, confused"
          />
        </div>

        <div className="field">
          <label>Weather</label>
          <input
            value={weather}
            onChange={(e) => setWeather(e.target.value)}
            placeholder="e.g. rainy, sunny"
          />
        </div>
      </div>

      <div className="field">
        <label>Journal entry</label>
        <textarea
          value={content}
          onChange={(e) => setContent(e.target.value)}
          placeholder="Write your journal here..."
          rows={10}
        />
      </div>

      <button className="primary-btn" onClick={handleSubmit} disabled={loading}>
        {loading ? "Analyzing..." : "Save & Analyze"}
      </button>
    </div>
  );
}
