/**
 * ChatPage — standalone emotional support chat.
 *
 * Layout: two-panel (left sidebar with session history, right panel for active chat).
 * Pre-check flow before every new chat.
 * Crisis detection on every user message.
 * Reuses existing: PrecheckModal, ChatPanel, CrisisBanner, detectCrisis,
 * submitPrecheck, useStreamingChat, supportNotificationStore.
 */

import { useState, useEffect, useCallback, useRef } from "react";
import { PlusCircle, MessageCircle, Trash2 } from "lucide-react";

import { fetchAllChatSessions, createChatSession, appendChatMessage, fetchChatSessionDetail } from "../api";
import { submitPrecheck } from "../api";
import { useStreamingChat } from "../hooks/useStreamingChat";
import { checkAndReportCrisis } from "../utils/crisisCheck";
import CrisisBanner from "../components/CrisisBanner";

import PrecheckModal from "../components/PrecheckModal";
import ChatPanel from "../components/ChatPanel";
import type { ChatMessage, PrecheckResponse } from "../types";
import type { SupportNotification } from "../utils/supportTypes";

interface SessionListItem {
  session_id: string;
  title?: string | null;
  last_message_preview?: string | null;
  created_at: string;
  updated_at: string;
}

interface ChatState {
  sessionId: string;
  title: string;
  messages: ChatMessage[];
  roundIndex: number;
  completed: boolean;
  /** Pre-check assigned role for this session; drives the system prompt tone */
  assignedRole?: string;
}

function buildWarmOpener(result: PrecheckResponse): string {
  const { role, reasons } = result;
  const roleGreeting: Record<string, string> = {
    "Emotional Support": "情绪接纳与共情陪伴",
    "Clarify Thinking": "梳理事实与澄清认知",
    "Meta Reflection": "从更高视角回顾模式",
  };
  const roleLabel = roleGreeting[role] ?? role;
  const note = reasons ? `\n\n（参考：${reasons.slice(0, 80)}）` : "";
  return `你好，感谢你今天的到来。我感受到你此刻的状态——${roleLabel}。${note}\n\n请告诉我，你想从哪里开始？`;
}

function formatDate(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

export default function ChatPage({ anonId }: { anonId: string }) {
  const [sessions, setSessions] = useState<SessionListItem[]>([]);
  const [activeSession, setActiveSession] = useState<ChatState | null>(null);
  const [showPrecheck, setShowPrecheck] = useState(false);
  const [pendingPrecheckResult, setPendingPrecheckResult] = useState<PrecheckResponse | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [streamingContent, setStreamingContent] = useState("");
  const [chatLoading, setChatLoading] = useState(false);
  const [showCrisisBanner, setShowCrisisBanner] = useState(false);
  const [sessionLoading, setSessionLoading] = useState(false);

  const messagesRef = useRef<ChatMessage[]>([]);
  const streamedRef = useRef("");
  const pendingResultRef = useRef<PrecheckResponse | null>(null);

  const { startStream } = useStreamingChat();

  // Keep refs in sync
  useEffect(() => { messagesRef.current = messages; }, [messages]);
  useEffect(() => { pendingResultRef.current = pendingPrecheckResult; }, [pendingPrecheckResult]);

  // Auto-dismiss crisis banner
  useEffect(() => {
    if (!showCrisisBanner) return;
    const t = setTimeout(() => setShowCrisisBanner(false), 10_000);
    return () => clearTimeout(t);
  }, [showCrisisBanner]);

  // Load session list on mount
  useEffect(() => {
    loadSessions();
  }, [anonId]);

  const loadSessions = useCallback(async () => {
    try {
      const data = await fetchAllChatSessions(anonId, "chat");
      setSessions(data.sessions ?? []);
    } catch (err) {
      console.error("[ChatPage] Failed to load sessions:", err);
    }
  }, [anonId]);

  // ---- Fire-and-forget: persist a message to the backend ----
  const saveMessage = useCallback(
    (role: "user" | "assistant", content: string, sessionId: string) => {
      appendChatMessage(sessionId, role, content).catch((err) =>
        console.error("[ChatPage] Failed to save message:", err)
      );
    },
    []
  );

  // ---- Load an existing session from the sidebar ----
  const loadSession = useCallback(async (item: SessionListItem) => {
    setSessionLoading(true);
    try {
      const session = await fetchChatSessionDetail(item.session_id);
      if (!session) return;

      const msgs: ChatMessage[] = (session.messages ?? []).map((m) => ({
        role: m.role as "user" | "assistant",
        content: m.content,
      }));

      const completed =
        msgs.length > 0 &&
        msgs[msgs.length - 1].role === "assistant";

      setActiveSession({
        sessionId: session.session_id,
        title: session.title ?? item.title ?? "New Chat",
        messages: msgs,
        roundIndex: 1,
        completed,
        // assignedRole defaults to undefined for sessions loaded from DB;
        // the backend falls back to "Emotional Support companion" in that case.
      });
      setMessages(msgs);
      setShowPrecheck(false);
      setPendingPrecheckResult(null);
    } catch (err) {
      console.error("[ChatPage] Failed to load session:", err);
    } finally {
      setSessionLoading(false);
    }
  }, []);

  // ---- Start a brand-new chat: trigger pre-check ----
  const handleNewChat = useCallback(() => {
    setActiveSession(null);
    setMessages([]);
    setStreamingContent("");
    setPendingPrecheckResult(null);
    setShowPrecheck(true);
  }, []);

  // ---- Pre-check completed: create session + warm opener ----
  const handlePrecheckComplete = useCallback(
    async (result: PrecheckResponse) => {
      setPendingPrecheckResult(result);
      setShowPrecheck(false);

      try {
        const session = await createChatSession(anonId, "chat");
        const warmOpener = buildWarmOpener(result);

        const openerMsg: ChatMessage = { role: "assistant", content: warmOpener };
        setMessages([openerMsg]);

        setActiveSession({
          sessionId: session.session_id,
          title: "New Chat",
          messages: [openerMsg],
          roundIndex: 1,
          completed: false,
          assignedRole: result.role,
        });

        // Persist opener immediately
        appendChatMessage(session.session_id, "assistant", warmOpener).catch((err) =>
          console.error("[ChatPage] Failed to save opener:", err)
        );
      } catch (err) {
        console.error("[ChatPage] Failed to create session:", err);
      }
    },
    [anonId]
  );

  const handlePrecheckSkip = useCallback(() => {
    setShowPrecheck(false);
    // No session created — stay in empty state
  }, []);

  // ---- Send a message ----
  const handleSendMessage = useCallback(
    async (userMessage: string) => {
      const session = activeSession;
      if (!session) return;

      const historySnapshot = [...messagesRef.current, { role: "user" as const, content: userMessage }];

      setMessages(historySnapshot);
      setChatLoading(true);
      setStreamingContent("");
      streamedRef.current = "";

      // ---- Crisis detection: backend-driven, single source of truth ----
      console.log("[CRISIS] chat sending", userMessage);
      checkAndReportCrisis(userMessage, "chat", anonId);

      const body = {
        anon_id: anonId,
        message: userMessage,
        history: historySnapshot,
        diary_content: undefined as string | undefined,
        assigned_role: session.assignedRole,
      };

      await startStream(
        body,
        (chunk) => {
          streamedRef.current += chunk;
          setStreamingContent(streamedRef.current);
        },
        () => {
          const finalContent = streamedRef.current;
          if (!finalContent) return;

          const assistantMsg: ChatMessage = { role: "assistant", content: finalContent };
          const nextMessages = [...messagesRef.current, assistantMsg];

          setMessages(nextMessages);
          setActiveSession((prev) =>
            prev ? { ...prev, messages: nextMessages } : prev
          );
          setStreamingContent("");
          streamedRef.current = "";

          // Persist both messages
          saveMessage("user", userMessage, session.sessionId);
          saveMessage("assistant", finalContent, session.sessionId);

          // Update sidebar session list (refresh to pick up new updated_at / title)
          loadSessions();
        },
        (errorMsg) => {
          setStreamingContent("");
          streamedRef.current = "";
          alert(errorMsg);
        }
      );

      setChatLoading(false);
    },
    [activeSession, anonId, startStream, saveMessage, loadSessions]
  );

  // ---- Delete a session (remove from list locally) ----
  const handleDeleteSession = useCallback(
    (e: React.MouseEvent, sessionId: string) => {
      e.stopPropagation();
      setSessions((prev) => prev.filter((s) => s.session_id !== sessionId));
      if (activeSession?.sessionId === sessionId) {
        setActiveSession(null);
        setMessages([]);
        setStreamingContent("");
        setPendingPrecheckResult(null);
        setShowPrecheck(false);
      }
    },
    [activeSession]
  );

  // ---- Active session title derived from the first user message ----
  const displayTitle = activeSession
    ? activeSession.title !== "New Chat"
      ? activeSession.title
      : messagesRef.current.find((m) => m.role === "user")?.content.slice(0, 30) ?? "New Chat"
    : "New Chat";

  const showChatPanel = !!activeSession && !showPrecheck;

  return (
    <div className="chat-page">
      {/* Left sidebar */}
      <aside className="chat-sidebar">
        <button className="chat-sidebar__new-btn" onClick={handleNewChat}>
          <PlusCircle size={16} />
          New Chat
        </button>

        <div className="chat-sidebar__sessions">
          {sessions.length === 0 && (
            <p className="chat-sidebar__empty">No conversations yet.</p>
          )}
          {sessions.map((item) => {
            const isActive = activeSession?.sessionId === item.session_id;
            return (
              <button
                key={item.session_id}
                className={`chat-sidebar__session ${isActive ? "active" : ""}`}
                onClick={() => loadSession(item)}
                title={item.last_message_preview ?? item.title ?? ""}
              >
                <div className="chat-sidebar__session-top">
                  <span className="chat-sidebar__session-title">
                    {item.title
                      ? item.title.length > 30
                        ? item.title.slice(0, 30) + "…"
                        : item.title
                      : item.last_message_preview
                      ? item.last_message_preview.length > 30
                        ? item.last_message_preview.slice(0, 30) + "…"
                        : item.last_message_preview
                      : "New Chat"}
                  </span>
                  <button
                    className="chat-sidebar__session-delete"
                    onClick={(e) => handleDeleteSession(e, item.session_id)}
                    title="Delete"
                    aria-label="Delete session"
                  >
                    <Trash2 size={12} />
                  </button>
                </div>
                <span className="chat-sidebar__session-date">
                  {formatDate(item.updated_at)}
                </span>
              </button>
            );
          })}
        </div>
      </aside>

      {/* Right panel */}
      <main className="chat-main">
        {showPrecheck ? (
          <PrecheckModal
            anonId={anonId}
            onComplete={handlePrecheckComplete}
            onSkip={handlePrecheckSkip}
            isOpen={showPrecheck}
            onClose={() => setShowPrecheck(false)}
          />
        ) : showChatPanel || sessionLoading ? (
          <>
            <div className="chat-page__header">
              <MessageCircle size={18} className="chat-page__header-icon" />
              <span className="chat-page__header-title">{displayTitle}</span>
            </div>
            <div className="chat-page__panel">
              <ChatPanel
                messages={messages}
                onSendMessage={handleSendMessage}
                loading={chatLoading}
                streamingContent={streamingContent}
                onNewChat={handleNewChat}
              />
            </div>
          </>
        ) : (
          <div className="chat-page__welcome">
            <div className="chat-page__welcome-icon">
              <MessageCircle size={48} strokeWidth={1.5} />
            </div>
            <h2 className="chat-page__welcome-title">Emotional Support Chat</h2>
            <p className="chat-page__welcome-sub">
              A safe space to talk. Start a new conversation or pick one from the left.
            </p>
            <button className="btn-primary chat-page__welcome-btn" onClick={handleNewChat}>
              <PlusCircle size={16} />
              Start New Chat
            </button>
          </div>
        )}
      </main>

      {showCrisisBanner && (
        <CrisisBanner onDismiss={() => setShowCrisisBanner(false)} />
      )}
    </div>
  );
}
