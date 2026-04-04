import { useState, useEffect, useCallback, useRef } from "react";
import { submitChat, submitJournal, submitPrecheck, continueChat, fetchLatestChatSession, createChatSession, appendChatMessage } from "../api";
import { useStreamingChat } from "../hooks/useStreamingChat";
import { checkAndReportCrisis } from "../utils/crisisCheck";
import { getStoredPrecheck, savePrecheckResult, clearPrecheckResult, type PrecheckStoredData } from "../utils";
import CrisisBanner from "./CrisisBanner";
import type {
  ChatMessage,
  ChatRequest,
  JournalResponse,
  PrecheckResponse,
  PrecheckRequest,
  ChatContinueResponse,
  JournalEntryResponse,
  JournalSubmitParams,
} from "../types";
import ChatPanel from "./ChatPanel";
import JournalPanel from "./JournalPanel";
import PrecheckModal from "./PrecheckModal";
import PrecheckStatusBar from "./PrecheckStatusBar";

interface Props {
  anonId: string;
  onViewHistory?: () => void;
  writeDate?: string | null;
  onClearWriteDate?: () => void;
}

export default function ChatJournalPage({ anonId, onViewHistory, writeDate, onClearWriteDate }: Props) {
  const [precheckResult, setPrecheckResult] = useState<PrecheckResponse | null>(null);
  const [hasSkippedPrecheck, setHasSkippedPrecheck] = useState(false);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [chatLoading, setChatLoading] = useState(false);
  const [streamingContent, setStreamingContent] = useState<string>("");
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  const [currentRound, setCurrentRound] = useState<number>(1);
  const [isSessionCompleted, setIsSessionCompleted] = useState(false);
  const [isHistoryOpen, setIsHistoryOpen] = useState(false);
  const [selectedEntry, setSelectedEntry] = useState<JournalEntryResponse | null>(null);
  const messagesRef = useRef<ChatMessage[]>([]);
  const streamedTextRef = useRef<string>("");
  const [chatSessionId, setChatSessionId] = useState<string | null>(null);
  /** Stores the content of the most recently submitted diary entry */
  const [lastDiaryContent, setLastDiaryContent] = useState<string>("");
  /** Ref so handleChat always reads the current value without stale-closure issues */
  const lastDiaryContentRef = useRef<string>("");
  useEffect(() => { lastDiaryContentRef.current = lastDiaryContent; }, [lastDiaryContent]);

  const { startStream, cancelStream } = useStreamingChat();

  // ---- Crisis banner state — shown when LLM detects crisis ----
  const [showCrisisBanner, setShowCrisisBanner] = useState(false);

  // Auto-dismiss after 10 seconds
  useEffect(() => {
    if (!showCrisisBanner) return;
    const t = setTimeout(() => setShowCrisisBanner(false), 10_000);
    return () => clearTimeout(t);
  }, [showCrisisBanner]);

  // ---- Load latest chat session on mount ----
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const session = await fetchLatestChatSession(anonId, "diary");
        if (cancelled) return;
        const msgs: ChatMessage[] = (session as any).messages ?? [];
        if (msgs.length > 0) {
          setMessages(msgs.map((m: { role: string; content: string }) => ({
            role: m.role as "user" | "assistant",
            content: m.content,
          })));
        }
        setChatSessionId((session as any).session_id ?? null);
        // Restore diary context so the AI still has it
        if ((session as any).diary_content) {
          setLastDiaryContent((session as any).diary_content);
        }
      } catch (err) {
        console.error("[ChatJournalPage] Failed to load chat session:", err);
      }
    })();
    return () => { cancelled = true; };
  }, [anonId]);

  useEffect(() => {
    messagesRef.current = messages;
  }, [messages]);

  // ---- Load precheck result from localStorage (24-hour expiry) ----
  useEffect(() => {
    const stored = getStoredPrecheck();
    if (stored) {
      setPrecheckResult({ role: stored.assigned_role, confidence: 0, reasons: "" });
      setHasSkippedPrecheck(false);
    } else {
      // No valid precheck — show the modal
      setIsModalOpen(true);
    }
  }, []);

  const handlePrecheckComplete = useCallback((result: PrecheckResponse) => {
    setPrecheckResult(result);
    setHasSkippedPrecheck(false);
    savePrecheckResult(result.role);
  }, []);

  const handlePrecheckSkip = useCallback(() => {
    setHasSkippedPrecheck(true);
    // On skip, store a "general support" sentinel so the bar shows immediately
    savePrecheckResult("general_support");
  }, []);

  const handleOpenModal = useCallback(() => {
    // "Change check-in" clears any stored result so a fresh 24-hour window starts
    clearPrecheckResult();
    setIsModalOpen(true);
  }, []);

  const handleCloseModal = useCallback(() => {
    setIsModalOpen(false);
  }, []);

  const handleOpenHistory = useCallback(() => {
    setIsHistoryOpen(true);
  }, []);

  const handleCloseHistory = useCallback(() => {
    setIsHistoryOpen(false);
  }, []);

  const handleSelectEntry = useCallback((entry: JournalEntryResponse) => {
    setSelectedEntry(entry);
    setIsHistoryOpen(false);
  }, []);

  const handleClearSelection = useCallback(() => {
    setSelectedEntry(null);
  }, []);

  // ---- Fire-and-forget helper: save a message to the chat session ----
  const saveMessage = useCallback(
    (role: "user" | "assistant", content: string) => {
      if (!chatSessionId) return;
      const isFirstUser = role === "user" && lastDiaryContentRef.current &&
        !messagesRef.current.some(m => m.role === "user");
      appendChatMessage(
        chatSessionId,
        role,
        content,
        isFirstUser ? lastDiaryContentRef.current : undefined
      ).catch((err) =>
        console.error("[ChatJournalPage] Failed to save message:", err)
      );
    },
    [chatSessionId]
  );

  // ---- Start a brand-new free-form chat session ----
  const handleNewChat = useCallback(async () => {
    cancelStream?.();
    setMessages([]);
    setStreamingContent("");
    setIsSessionCompleted(false);
    setCurrentSessionId(null);
    streamedTextRef.current = "";
    try {
      const session = await createChatSession(anonId, "diary");
      setChatSessionId(session.session_id);
    } catch (err) {
      console.error("[ChatJournalPage] Failed to create new session:", err);
    }
  }, [cancelStream, anonId]);

  const handleChat = async (userMessage: string) => {
    const newUserMessage: ChatMessage = { role: "user", content: userMessage };
    const historySnapshot = [...messagesRef.current, newUserMessage];

    setMessages(historySnapshot);
    setChatLoading(true);
    setStreamingContent("");
    streamedTextRef.current = "";

    // ---- Crisis detection: backend-driven, single source of truth ----
    console.log("[CRISIS] chat sending", userMessage.slice(0, 100));
    checkAndReportCrisis(userMessage, "chat", anonId);

    const useStreaming = !currentSessionId || isSessionCompleted;

    if (useStreaming) {
      console.log("3. diary_content being sent to chat (lastDiaryContentRef.current):", lastDiaryContentRef.current?.slice(0, 100) ?? "EMPTY/UNDEFINED");

      const request: ChatRequest = {
        anon_id: anonId,
        message: userMessage,
        history: historySnapshot,
        diary_content: lastDiaryContentRef.current || undefined,
        assigned_role: precheckResult?.role ?? undefined,
      };

      console.log("4. full chat request body:", JSON.stringify(request));

      await startStream(
        request,
        (chunk) => {
          streamedTextRef.current += chunk;
          setStreamingContent(streamedTextRef.current);
        },
        () => {
          const finalContent = streamedTextRef.current;
          if (finalContent) {
            const assistantMessage: ChatMessage = { role: "assistant", content: finalContent };
            setMessages((prev) => [...prev, assistantMessage]);
            // Persist both user message and assistant reply
            saveMessage("user", userMessage);
            saveMessage("assistant", finalContent);
          }
          setStreamingContent("");
          streamedTextRef.current = "";
        },
        (errorMsg) => {
          setStreamingContent("");
          streamedTextRef.current = "";
          alert(errorMsg);
        }
      );

    } else {
      try {
        const response: ChatContinueResponse = await continueChat({
          session_id: currentSessionId!,
          user_message: userMessage
        });

        const assistantMessage: ChatMessage = {
          role: "assistant",
          content: response.assistant_message
        };

        setMessages((prev) => [...prev, assistantMessage]);
        setCurrentRound(response.round_index);

        // Persist both messages to the free-form chat session
        saveMessage("user", userMessage);
        saveMessage("assistant", response.assistant_message);

        if (response.status === "completed") {
          setIsSessionCompleted(true);
        }
      } catch (error) {
        console.error("Chat continue failed:", error);
        alert("Chat failed. Please try again.");
      }
    }

    setChatLoading(false);
  };

  const handleJournalSubmit = async (payload: {
    content: string;
    mood?: string;
    weather?: string;
  }) => {
    // Synchronously update ref BEFORE the API call so handleChat always sees the value
    setLastDiaryContent(payload.content);
    lastDiaryContentRef.current = payload.content;

    console.log("1. diary text before save:", payload.content.slice(0, 100));

    try {
      const result: JournalResponse = await submitJournal({
        anon_id: anonId,
        ...payload
      });

      console.log("2. save succeeded, diary content:", payload.content.slice(0, 100));

      const riskLevel = result.risk?.risk_level ?? "?";

      // ---- Crisis detection: backend-driven, single source of truth ----
      console.log("[CRISIS] diary sending", payload.content.slice(0, 100));
      checkAndReportCrisis(payload.content, "diary", anonId);

      // NEW diary entry — always start with a clean history, no carry-over from previous sessions
      setMessages([]);
      messagesRef.current = [];

      const newMessages: ChatMessage[] = [];

      // NOTE: diary content is now injected via the system prompt — no user-message injection needed.
      if (riskLevel >= 3) {
        newMessages.push({
          role: "assistant",
          content: `I've read your journal entry.\n\n⚠️ Risk Level: ${riskLevel}.\nIf you have strong thoughts of self-harm, please call a crisis hotline or seek emergency help immediately.`
        });
      } else {
        if (result.rounds?.b1?.text) {
          newMessages.push({
            role: "assistant",
            content: result.rounds.b1.text
          });
        }

        if (result.session_id) {
          setCurrentSessionId(result.session_id);
          setCurrentRound(result.round_index || 1);
          setIsSessionCompleted(false);
        }
      }

      // Now messagesRef.current is guaranteed empty — safe to append
      const nextMessages = [...messagesRef.current, ...newMessages];
      setMessages(nextMessages);
      messagesRef.current = nextMessages;

      // Auto-trigger chat: send the diary content as the first user message,
      // with diary_content injected into the system prompt for deep context.
      // history is empty (clean slate) for the new diary session.
      setChatLoading(true);
      handleChat(payload.content);
    } catch (err: unknown) {
      console.error("Journal submission failed:", err);
      let msg: string | null = null;
      if (err && typeof err === "object" && "response" in err) {
        const res = (err as { response?: { data?: { detail?: string | string[] }; status?: number } }).response;
        if (res?.data?.detail != null) {
          msg = Array.isArray(res.data.detail) ? res.data.detail.join("\n") : String(res.data.detail);
        } else if (res?.status === 404) {
          msg = "User not found.";
        } else if (res?.status === 400) {
          msg = "Please complete the Pre-check first.";
        }
      } else if (err instanceof Error) {
        if (err.message.includes("Network") || err.message.includes("timeout")) {
          msg = "Cannot connect to backend. Please make sure the server is running.";
        }
      }
      alert(msg || "Failed to submit journal. Please try again.");
    }
  };

  const handleJournalSubmitWithMeta = async (payload: JournalSubmitParams) => {
    // Synchronously update ref BEFORE the API call so handleChat always sees the value
    setLastDiaryContent(payload.content);
    lastDiaryContentRef.current = payload.content;

    console.log("1. diary text before save:", payload.content.slice(0, 100));

    try {
      const result: JournalResponse = await submitJournal({
        anon_id: anonId,
        content: payload.content,
        mood: payload.mood,
        weather: payload.weather,
        title: payload.title,
        entry_date: payload.entry_date,
        source_type: payload.source_type,
        original_input_text: payload.original_input_text,
        source_file_path: payload.source_file_path,
        input_metadata: payload.input_metadata,
      });

      console.log("2. save succeeded, diary content:", payload.content.slice(0, 100));

      const riskLevel = result.risk?.risk_level ?? "?";

      // ---- Crisis detection: backend-driven, single source of truth ----
      console.log("[CRISIS] diary sending", payload.content.slice(0, 100));
      checkAndReportCrisis(payload.content, "diary", anonId);

      // NEW diary entry — always start with a clean history, no carry-over from previous sessions
      setMessages([]);
      messagesRef.current = [];

      const newMessages: ChatMessage[] = [];

      // NOTE: diary content is now injected via the system prompt — no user-message injection needed.
      if (riskLevel >= 3) {
        newMessages.push({
          role: "assistant",
          content: `I've read your journal entry.\n\n⚠️ Risk Level: ${riskLevel}.\nIf you have strong thoughts of self-harm, please call a crisis hotline or seek emergency help immediately.`
        });
      } else {
        if (result.rounds?.b1?.text) {
          newMessages.push({
            role: "assistant",
            content: result.rounds.b1.text
          });
        }

        if (result.session_id) {
          setCurrentSessionId(result.session_id);
          setCurrentRound(result.round_index || 1);
          setIsSessionCompleted(false);
        }
      }

      // Now messagesRef.current is guaranteed empty — safe to append
      const nextMessages = [...messagesRef.current, ...newMessages];
      setMessages(nextMessages);
      messagesRef.current = nextMessages;

      // Auto-trigger chat: send the diary content as the first user message,
      // with diary_content injected into the system prompt for deep context.
      // history is empty (clean slate) for the new diary session.
      setChatLoading(true);
      handleChat(payload.content);
    } catch (err: unknown) {
      console.error("Journal submission failed:", err);
      let msg: string | null = null;
      if (err && typeof err === "object" && "response" in err) {
        const res = (err as { response?: { data?: { detail?: string | string[] }; status?: number } }).response;
        if (res?.data?.detail != null) {
          msg = Array.isArray(res.data.detail) ? res.data.detail.join("\n") : String(res.data.detail);
        } else if (res?.status === 404) {
          msg = "User not found.";
        } else if (res?.status === 400) {
          msg = "Please complete the Pre-check first.";
        }
      } else if (err instanceof Error) {
        if (err.message.includes("Network") || err.message.includes("timeout")) {
          msg = "Cannot connect to backend. Please make sure the server is running.";
        }
      }
      alert(msg || "Failed to submit journal. Please try again.");
    }
  };

  return (
    <div className="chat-journal-page">
      <PrecheckModal
        anonId={anonId}
        onComplete={handlePrecheckComplete}
        onSkip={handlePrecheckSkip}
        isOpen={isModalOpen}
        onClose={handleCloseModal}
      />

      <PrecheckStatusBar
        precheckResult={precheckResult}
        onChangeCheckin={handleOpenModal}
      />

      <div className="chat-journal-layout">
        <div className="chat-panel-container">
          <ChatPanel
            messages={messages}
            onSendMessage={handleChat}
            loading={chatLoading}
            streamingContent={streamingContent}
            onNewChat={handleNewChat}
            hasUnsavedJournal={!lastDiaryContent}
          />
        </div>

        <div className="journal-panel-container">
          <JournalPanel
            onSubmit={handleJournalSubmit}
            onSubmitWithMeta={handleJournalSubmitWithMeta}
            lastResult={null}
            anonId={anonId}
            onHistoryClick={onViewHistory || (() => {})}
            selectedEntry={selectedEntry}
            onClearSelection={handleClearSelection}
            today={new Date().toISOString().split("T")[0]}
            writeDate={writeDate ?? undefined}
            onClearWriteDate={onClearWriteDate}
          />
        </div>
      </div>

      {/* Gentle banner shown when LLM crisis detection triggers */}
      {showCrisisBanner && (
        <CrisisBanner onDismiss={() => setShowCrisisBanner(false)} />
      )}
    </div>
  );
}
