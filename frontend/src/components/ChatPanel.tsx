import { useState, useRef, useEffect } from "react";
import { Send } from "lucide-react";
import type { ChatMessage } from "../types";

interface Props {
  messages: ChatMessage[];
  onSendMessage: (message: string) => void;
  loading: boolean;
}

export default function ChatPanel({ messages, onSendMessage, loading }: Props) {
  const [input, setInput] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (input.trim() && !loading) {
      onSendMessage(input.trim());
      setInput("");
    }
  };

  return (
    <div className="chat-panel">
      <div className="chat-header">
        <h2>AI Therapist</h2>
        <p className="chat-subtitle">A safe space to talk</p>
      </div>

      <div className="chat-messages">
        {messages.length === 0 ? (
          <div className="chat-empty">
            <p>Hello! I'm here to listen and support you.</p>
            <p>Feel free to share what's on your mind.</p>
          </div>
        ) : (
          messages.map((msg, index) => (
            <div
              key={index}
              className={`chat-message ${msg.role === "user" ? "user" : "assistant"}`}
            >
              <div className="message-bubble">
                {msg.content}
              </div>
            </div>
          ))
        )}
        {loading && (
          <div className="chat-message assistant">
            <div className="message-bubble loading">
              <span>Thinking...</span>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <form className="chat-input-form" onSubmit={handleSubmit}>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Type your message..."
          disabled={loading}
        />
        <button type="submit" disabled={loading || !input.trim()}>
          <Send size={18} />
        </button>
      </form>
    </div>
  );
}
