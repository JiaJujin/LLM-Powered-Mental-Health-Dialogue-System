import { History } from "lucide-react";

interface Props {
  items: string[];
}

export default function AnalysisHistoryCard({ items }: Props) {
  return (
    <div className="card history-card">
      <div className="card-title with-icon">
        <History size={18} />
        <span>Analysis History</span>
      </div>

      <div className="history-list">
        {items.length === 0 ? (
          <div className="empty-small">No previous analysis history yet</div>
        ) : (
          items.map((item, idx) => (
            <div key={idx} className={`history-item ${idx === 0 ? "active" : ""}`}>
              {item}
            </div>
          ))
        )}
      </div>
    </div>
  );
}
