import { useState, useRef, useEffect } from "react";
import { Send, Mic, MicOff, PlusCircle } from "lucide-react";
import { useVoiceInput } from "../hooks/useVoiceInput";
import type { ChatMessage } from "../types";

interface Props {
  messages: ChatMessage[];
  onSendMessage: (message: string) => void;
  loading: boolean;
  /** Real-time streaming content - shown as the last assistant message while streaming */
  streamingContent?: string;
  /** Fires when the user clicks "New Chat" — clears the conversation */
  onNewChat?: () => void;
  /** When true, show the guidance prompt to save entry first */
  hasUnsavedJournal?: boolean;
}

export default function ChatPanel({ messages, onSendMessage, loading, streamingContent, onNewChat, hasUnsavedJournal }: Props) {
  const [input, setInput] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // ---- Voice input via shared hook ----
  const {
    isRecording,
    isTranscribing,
    interimTranscript,
    accumulatedTranscript,
    recordingTime,
    error: voiceError,
    toggleRecording,
  } = useVoiceInput({
    onFinal: (text) => {
      setInput((prev) => {
        const base = prev.trim() ? `${prev.trim()}\n${text}` : text;
        return base;
      });
    },
    onError: () => {},
  });

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingContent]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    // Use accumulated + interim as the final value (user stops recording then sends)
    const finalValue = accumulatedTranscript.trim() || input.trim();
    if (finalValue && !loading) {
      onSendMessage(finalValue);
      setInput("");
    }
  };

  // Determine if we should show streaming indicator
  const showStreaming = loading && streamingContent !== undefined && streamingContent !== "";

  // ---- Live display: solid accumulated text + gray interim transcript ----
  const isVoiceActive = isRecording || isTranscribing;
  const liveInputValue = isVoiceActive
    ? (accumulatedTranscript ? `${accumulatedTranscript}\n` : "") + interimTranscript
    : input;

  return (
    <div className="chat-panel">
      <div className="chat-header">
        <div className="chat-header__left">
          <h2>Journal Companion</h2>
          <p className="chat-subtitle">Chat about what you just wrote</p>
        </div>
        {onNewChat && messages.length > 0 && (
          <button
            type="button"
            className="btn-new-chat"
            onClick={onNewChat}
            title="Start a new conversation"
          >
            <PlusCircle size={15} />
            New Chat
          </button>
        )}
      </div>

      {hasUnsavedJournal && (
        <div className="chat-guidance">
          Save your entry first, then talk to your AI companion about it.
        </div>
      )}

      <div className="chat-messages">
        {messages.length === 0 && !showStreaming ? (
          <div className="chat-empty">
            <p>Hello! I'm here to listen and support you.</p>
            <p>Feel free to share what's on your mind.</p>
          </div>
        ) : (
          <>
            {messages.map((msg, index) => (
              <div
                key={index}
                className={`chat-message ${msg.role === "user" ? "user" : "assistant"}`}
              >
                <div className="message-bubble">
                  {msg.content}
                </div>
              </div>
            ))}
            {/* Streaming message - shown incrementally */}
            {showStreaming && (
              <div className="chat-message assistant">
                <div className="message-bubble">
                  {streamingContent}
                  <span className="typing-cursor">|</span>
                </div>
              </div>
            )}
          </>
        )}
        {loading && !showStreaming && (
          <div className="chat-message assistant">
            <div className="message-bubble loading">
              <span>AI is typing...</span>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Voice error */}
      {voiceError && (
        <div className="chat-voice-error">{voiceError}</div>
      )}

      <form className="chat-input-form" onSubmit={handleSubmit}>
        <input
          type="text"
          value={liveInputValue}
          onChange={(e) => {
            // Allow editing only when not recording
            if (!isVoiceActive) setInput(e.target.value);
          }}
          placeholder={isVoiceActive ? "Listening..." : "Type your message..."}
          disabled={loading && !isVoiceActive}
          style={{
            color: isVoiceActive && !accumulatedTranscript ? "#a8a29e" : undefined,
            fontStyle: isVoiceActive && !accumulatedTranscript ? "italic" : undefined,
          }}
        />

        {/* Mic button */}
        <button
          type="button"
          className={`chat-mic-btn ${isRecording ? "recording" : ""} ${isTranscribing ? "transcribing" : ""}`}
          title={isRecording ? "Stop recording" : "Voice input"}
          onClick={toggleRecording}
          disabled={loading}
        >
          {isRecording || isTranscribing ? (
            <span className="mic-icon-wrapper">
              <MicOff size={18} />
              {isRecording && <span className="recording-dot-sm" />}
            </span>
          ) : (
            <Mic size={18} />
          )}
        </button>

        {isRecording && (
          <span className="chat-recording-timer">
            {Math.floor(recordingTime / 60).toString().padStart(2, "0")}:
            {(recordingTime % 60).toString().padStart(2, "0")}
          </span>
        )}

        <button type="submit" disabled={loading || !(accumulatedTranscript.trim() || input.trim())}>
          <Send size={18} />
        </button>
      </form>
    </div>
  );
}
