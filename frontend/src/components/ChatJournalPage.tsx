import { useState, useEffect, useCallback, useRef } from "react";
import { submitChat, submitJournal, submitPrecheck, continueChat } from "../api";
import type {
  ChatMessage,
  ChatRequest,
  JournalResponse,
  PrecheckResponse,
  PrecheckRequest,
  ChatContinueResponse,
  JournalEntryResponse
} from "../types";
import ChatPanel from "./ChatPanel";
import JournalPanel from "./JournalPanel";
import PrecheckModal from "./PrecheckModal";
import PrecheckStatusBar from "./PrecheckStatusBar";

const STORAGE_KEY = "mj_precheck_done";
const STORAGE_ROLE_KEY = "mj_precheck_role";

interface Props {
  anonId: string;
  onViewHistory?: () => void;
}

export default function ChatJournalPage({ anonId, onViewHistory }: Props) {
  const [precheckResult, setPrecheckResult] = useState<PrecheckResponse | null>(null);
  const [hasSkippedPrecheck, setHasSkippedPrecheck] = useState(false);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [chatLoading, setChatLoading] = useState(false);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  const [currentRound, setCurrentRound] = useState<number>(1);
  const [isSessionCompleted, setIsSessionCompleted] = useState(false);
  const [isHistoryOpen, setIsHistoryOpen] = useState(false);
  const [selectedEntry, setSelectedEntry] = useState<JournalEntryResponse | null>(null);
  const messagesRef = useRef<ChatMessage[]>([]);

  useEffect(() => {
    messagesRef.current = messages;
  }, [messages]);

  // Load precheck state from localStorage on mount
  useEffect(() => {
    const storedDone = localStorage.getItem(STORAGE_KEY);
    const storedRole = localStorage.getItem(STORAGE_ROLE_KEY);

    if (storedDone === "true" && storedRole) {
      setPrecheckResult({ role: storedRole, confidence: 0, reasons: "" });
      setHasSkippedPrecheck(false);
    } else if (storedDone === "skipped") {
      setHasSkippedPrecheck(true);
    } else {
      // First time - show modal
      setIsModalOpen(true);
    }
  }, []);

  const handlePrecheckComplete = useCallback((result: PrecheckResponse) => {
    setPrecheckResult(result);
    setHasSkippedPrecheck(false);
    localStorage.setItem(STORAGE_KEY, "true");
    localStorage.setItem(STORAGE_ROLE_KEY, result.role);
  }, []);

  const handlePrecheckSkip = useCallback(() => {
    setHasSkippedPrecheck(true);
    localStorage.setItem(STORAGE_KEY, "skipped");
  }, []);

  const handleOpenModal = useCallback(() => {
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

  const handleChat = async (userMessage: string) => {
    const newUserMessage: ChatMessage = { role: "user", content: userMessage };
    const historySnapshot = [...messagesRef.current, newUserMessage];
    setMessages(historySnapshot);
    setChatLoading(true);

    try {
      // Check if there's an active therapy session
      if (currentSessionId && !isSessionCompleted) {
        // Use therapy chat continue
        const response: ChatContinueResponse = await continueChat({
          session_id: currentSessionId,
          user_message: userMessage
        });

        const assistantMessage: ChatMessage = {
          role: "assistant",
          content: response.assistant_message
        };

        setMessages(prev => [...prev, assistantMessage]);
        setCurrentRound(response.round_index);

        if (response.status === "completed") {
          setIsSessionCompleted(true);
        }
      } else {
        // Use regular chat (no active session or session completed)
        const request: ChatRequest = {
          anon_id: anonId,
          message: userMessage,
          history: historySnapshot
        };
        const response = await submitChat(request);

        const assistantMessage: ChatMessage = {
          role: "assistant",
          content: response.reply
        };
        setMessages(prev => [...prev, assistantMessage]);
      }
    } catch (error) {
      console.error("Chat failed:", error);
      // Try without precheck context - use default
      try {
        const request: ChatRequest = {
          anon_id: anonId,
          message: userMessage,
          history: historySnapshot
        };
        const response = await submitChat(request);
        const assistantMessage: ChatMessage = {
          role: "assistant",
          content: response.reply
        };
        setMessages(prev => [...prev, assistantMessage]);
      } catch (retryError) {
        console.error("Chat retry failed:", retryError);
        alert("Failed to get response. Please try again.");
      }
    } finally {
      setChatLoading(false);
    }
  };

  const handleJournalSubmit = async (payload: {
    content: string;
    mood?: string;
    weather?: string;
  }) => {
    try {
      const result: JournalResponse = await submitJournal({
        anon_id: anonId,
        ...payload
      });

      const riskLevel = result.risk?.risk_level ?? "?";
      const riskTrigger = result.risk?.trigger ? `提示：${result.risk.trigger}` : "";

      // Build messages based on risk level
      const newMessages: ChatMessage[] = [];

      // Add user diary message
      const diaryUserMsg: ChatMessage = {
        role: "user",
        content: `我刚写了一篇日记：\n\n${payload.content}`
      };
      newMessages.push(diaryUserMsg);

      if (riskLevel >= 3) {
        // High risk - show warning only
        newMessages.push({
          role: "assistant",
          content: `我已读完你的日记。\n\n⚠️ 风险等级：${riskLevel}。\n${riskTrigger}\n\n如果你有强烈的自我伤害想法，请立即拨打心理危机干预热线或寻求紧急帮助。`
        });
      } else {
        // Normal flow - add B1 response only (no risk prompt in chat)
        if (result.rounds?.b1?.text) {
          newMessages.push({
            role: "assistant",
            content: result.rounds.b1.text
          });
        }

        // Set up session tracking if session_id is returned
        if (result.session_id) {
          setCurrentSessionId(result.session_id);
          setCurrentRound(result.round_index || 1);
          setIsSessionCompleted(false);
        }
      }

      const nextMessages = [...messagesRef.current, ...newMessages];
      setMessages(nextMessages);
    } catch (err: unknown) {
      console.error("Journal submission failed:", err);
      let msg: string | null = null;
      if (err && typeof err === "object" && "response" in err) {
        const res = (err as { response?: { data?: { detail?: string | string[] }; status?: number } }).response;
        if (res?.data?.detail != null) {
          msg = Array.isArray(res.data.detail) ? res.data.detail.join("\n") : String(res.data.detail);
        } else if (res?.status === 404) {
          msg = "用户不存在";
        } else if (res?.status === 400) {
          msg = "请先完成 Pre-check";
        }
      } else if (err instanceof Error) {
        if (err.message.includes("Network") || err.message.includes("timeout")) {
          msg = "无法连接后端，请确认服务已启动";
        }
      }
      alert(msg || "提交日记失败，请重试。");
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
          />
        </div>

        <div className="journal-panel-container">
          <JournalPanel
            onSubmit={handleJournalSubmit}
            lastResult={null}
            anonId={anonId}
            onHistoryClick={onViewHistory || (() => {})}
            selectedEntry={selectedEntry}
            onClearSelection={handleClearSelection}
          />
        </div>
      </div>
    </div>
  );
}
