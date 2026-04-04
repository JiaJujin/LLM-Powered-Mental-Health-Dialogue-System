import {
  MessageSquare,
  MessageCircle,
  BarChart3,
  BookOpen,
  History,
  HeartHandshake,
} from "lucide-react";
import type { AppTab } from "../types";
import type { ReactNode } from "react";
import { useSupportNotifications } from "../store/supportNotificationStore";

interface Props {
  activeTab: AppTab;
  onChange: (tab: AppTab) => void;
}

export default function Sidebar({ activeTab, onChange }: Props) {
  const { state: supportState } = useSupportNotifications();

  const items: { key: AppTab; label: string; icon: ReactNode }[] = [
    { key: "chat-journal",     label: "Write",         icon: <BookOpen size={18} /> },
    { key: "journal-history", label: "History",       icon: <History size={18} /> },
    { key: "chat",             label: "Chat",           icon: <MessageCircle size={18} /> },
    { key: "insights",         label: "Insights",       icon: <BarChart3 size={18} /> },
    { key: "my-support",      label: "My Support",    icon: <HeartHandshake size={18} /> },
  ];

  return (
    <aside className="sidebar">
      <div className="brand">MJ</div>

      <nav className="sidebar-nav">
        {items.map((item) => {
          // Which badge to show for this nav item
          const badgeCount =
            item.key === "my-support"
              ? supportState.unreadCount
              : 0;

          return (
            <button
              key={item.key}
              className={`sidebar-link ${activeTab === item.key ? "active" : ""}`}
              onClick={() => onChange(item.key)}
            >
              <span className="sidebar-link__icon">
                {item.icon}
                {badgeCount > 0 && (
                  <span className="sidebar-badge">{badgeCount}</span>
                )}
              </span>
              <span>{item.label}</span>
            </button>
          );
        })}
      </nav>
    </aside>
  );
}
