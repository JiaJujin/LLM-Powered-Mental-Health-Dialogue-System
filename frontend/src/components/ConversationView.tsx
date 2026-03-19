import type { JournalResponse } from "../types";

interface Props {
  data: JournalResponse;
}

export default function ConversationView({ data }: Props) {
  const rounds = [
    { key: "b1", title: "Round 1 · Emotional Reflection" },
    { key: "b2", title: "Round 2 · Cognitive Exploration" },
    { key: "b3", title: "Round 3 · Value & Action" }
  ] as const;

  return (
    <div className="conversation-stack">
      {rounds.map((round) => {
        const item = data.rounds[round.key];
        if (!item) return null;

        return (
          <div key={round.key} className="conversation-card">
            <div className="conversation-title">{round.title}</div>
            <div className="conversation-text">{item.text}</div>
          </div>
        );
      })}
    </div>
  );
}
