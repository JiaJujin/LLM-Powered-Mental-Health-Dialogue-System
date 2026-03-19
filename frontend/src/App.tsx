import { useMemo, useState } from "react";
import Sidebar from "./components/Sidebar";
import ChatJournalPage from "./components/ChatJournalPage";
import InsightsPage from "./components/InsightsPage";
import HistoryPage from "./components/HistoryPage";
import JournalDetailPage from "./components/JournalDetailPage";
import { getOrCreateAnonId } from "./utils";
import type { AppTab } from "./types";

export default function App() {
  const anonId = useMemo(() => getOrCreateAnonId(), []);
  const [activeTab, setActiveTab] = useState<AppTab>("chat-journal");
  const [selectedEntryId, setSelectedEntryId] = useState<number | null>(null);

  const handleViewHistory = () => {
    setSelectedEntryId(null);
    setActiveTab("journal-history");
  };

  const handleViewDetail = (entryId: number) => {
    setSelectedEntryId(entryId);
    setActiveTab("journal-detail");
  };

  const handleBackToHistory = () => {
    setSelectedEntryId(null);
    setActiveTab("journal-history");
  };

  return (
    <div className="app-shell">
      <Sidebar activeTab={activeTab} onChange={setActiveTab} />

      <main className="app-main">
        {activeTab === "chat-journal" && (
          <ChatJournalPage 
            anonId={anonId} 
            onViewHistory={handleViewHistory}
          />
        )}

        {activeTab === "journal-history" && (
          <HistoryPage 
            anonId={anonId} 
            onViewDetail={handleViewDetail}
          />
        )}

        {activeTab === "journal-detail" && selectedEntryId && (
          <JournalDetailPage
            anonId={anonId}
            entryId={selectedEntryId}
            onBack={handleBackToHistory}
          />
        )}

        {activeTab === "insights" && (
          <InsightsPage anonId={anonId} />
        )}
      </main>
    </div>
  );
}
