import { useMemo, useState } from "react";
import Sidebar from "./components/Sidebar";
import ChatJournalPage from "./components/ChatJournalPage";
import InsightsPage from "./components/InsightsPage";
import HistoryPage from "./components/HistoryPage";
import JournalDetailPage from "./components/JournalDetailPage";
import SupportDashboard from "./pages/SupportDashboard";
import MySupport from "./pages/MySupport";
import ChatPage from "./pages/ChatPage";
import { getOrCreateAnonId } from "./utils";
import type { AppTab } from "./types";

export default function App() {
  const anonId = useMemo(() => getOrCreateAnonId(), []);
  const [activeTab, setActiveTab] = useState<AppTab>("chat-journal");
  const [selectedEntryId, setSelectedEntryId] = useState<number | null>(null);
  const [writeDate, setWriteDate] = useState<string | null>(null);

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

  const handleGoToWriteWithDate = (date: string) => {
    setWriteDate(date);
    setActiveTab("chat-journal");
  };

  const handleBackToToday = () => {
    setWriteDate(null);
  };

  return (
    <div className="app-shell">
      <Sidebar activeTab={activeTab} onChange={setActiveTab} />

      <main className="app-main">
        {activeTab === "chat-journal" && (
          <ChatJournalPage
            anonId={anonId}
            onViewHistory={handleViewHistory}
            writeDate={writeDate}
            onClearWriteDate={handleBackToToday}
          />
        )}

        {activeTab === "journal-history" && (
          <HistoryPage
            anonId={anonId}
            onViewDetail={handleViewDetail}
            onGoToWriteWithDate={handleGoToWriteWithDate}
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
          <InsightsPage anonId={anonId} onGoToWrite={() => setActiveTab("chat-journal")} />
        )}

        {activeTab === "support" && (
          <SupportDashboard />
        )}

        {activeTab === "my-support" && (
          <MySupport userId={anonId} />
        )}

        {activeTab === "chat" && (
          <ChatPage anonId={anonId} />
        )}
      </main>
    </div>
  );
}
