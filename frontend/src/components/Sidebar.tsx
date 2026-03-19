import { MessageSquare, BarChart3, BookOpen, History } from "lucide-react";
import type { AppTab } from "../types";

interface Props {
  activeTab: AppTab;
  onChange: (tab: AppTab) => void;
}

export default function Sidebar({ activeTab, onChange }: Props) {
  const items: { key: AppTab; label: string; icon: JSX.Element }[] = [
    { key: "chat-journal", label: "Write", icon: <BookOpen size={18} /> },
    { key: "journal-history", label: "History", icon: <History size={18} /> },
    { key: "insights", label: "Insights", icon: <BarChart3 size={18} /> }
  ];

  return (
    <aside className="sidebar">
      <div className="brand">MJ</div>

      <nav className="sidebar-nav">
        {items.map((item) => (
          <button
            key={item.key}
            className={`sidebar-link ${activeTab === item.key ? "active" : ""}`}
            onClick={() => onChange(item.key)}
          >
            {item.icon}
            <span>{item.label}</span>
          </button>
        ))}
      </nav>
    </aside>
  );
}
