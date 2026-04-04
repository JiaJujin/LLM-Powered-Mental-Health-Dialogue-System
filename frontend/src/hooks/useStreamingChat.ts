import { useState, useCallback, useRef } from "react";
import type { ChatMessage, ChatRequest } from "../types";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "/api";
// 60s 后端超时保持一致
const TIMEOUT_MS = 60_000;

export interface StreamingState {
  isStreaming: boolean;
  error: string | null;
  currentContent: string;
}

/**
 * Hook for handling streaming chatbot responses.
 * Manages SSE connection, incremental text updates, and error handling.
 *
 * 关键调试：
 * - parsed.content      → 正常显示的聊天内容
 * - parsed.reasoning_content → 智谱 thinking 过程（会打印到控制台，不显示给用户）
 *   如果 reasoning_content 很长而 content 为空，说明模型仍处于 thinking 模式（应该被禁用）
 */
export function useStreamingChat() {
  const [state, setState] = useState<StreamingState>({
    isStreaming: false,
    error: null,
    currentContent: "",
  });
  const abortControllerRef = useRef<AbortController | null>(null);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const startStream = useCallback(
    async (
      request: ChatRequest,
      onChunk: (text: string) => void,
      onDone: () => void,
      onError: (msg: string) => void
    ) => {
      // Cancel any existing stream
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }

      const controller = new AbortController();
      abortControllerRef.current = controller;

      setState({ isStreaming: true, error: null, currentContent: "" });

      const startTime = Date.now();
      let chunkCount = 0;
      let firstChunkTime: number | null = null;

      console.log("[STREAM] Starting stream request:", {
        endpoint: `${API_BASE}/chat/stream`,
        message: request.message,
        historyLength: request.history?.length ?? 0,
        timeout: TIMEOUT_MS,
      });

      try {
        const response = await fetch(`${API_BASE}/chat/stream`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(request),
          signal: controller.signal,
        });

        if (!response.ok) {
          const raw = await response.text();
          let detail = `HTTP ${response.status}`;
          try {
            const errorData = JSON.parse(raw) as { detail?: unknown };
            if (errorData.detail != null) {
              detail =
                typeof errorData.detail === "string"
                  ? errorData.detail
                  : Array.isArray(errorData.detail)
                    ? errorData.detail.map(String).join("\n")
                    : JSON.stringify(errorData.detail);
            }
          } catch {
            if (raw.trim()) detail = raw.slice(0, 500);
          }
          throw new Error(detail);
        }

        const reader = response.body!.getReader();
        const decoder = new TextDecoder();
        let buffer = "";
        let elapsed = 0;

        console.log("[STREAM] Response received, starting to read chunks...");

        while (true) {
          // Check timeout every chunk
          elapsed = Date.now() - startTime;
          if (elapsed > TIMEOUT_MS) {
            reader.cancel();
            throw new Error(`响应超时（${TIMEOUT_MS / 1000}秒），请检查网络或重试`);
          }

          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() ?? "";

          for (const line of lines) {
            if (!line.startsWith("data: ")) continue;
            const data = line.slice(6).trim();
            if (data === "[DONE]") {
              console.log("[STREAM] Received [DONE], stream complete");
              reader.cancel();
              break;
            }
            let parsed: {
              content?: string;
              error?: string;
              reasoning_content?: string;
            };
            try {
              parsed = JSON.parse(data);
            } catch {
              continue;
            }
            if (parsed.error) {
              reader.cancel();
              throw new Error(parsed.error);
            }
            chunkCount += 1;

            if (firstChunkTime === null) {
              firstChunkTime = Date.now();
              const ttft = firstChunkTime - startTime;
              console.log(
                `[STREAM] FIRST CHUNK  ttft=${ttft}ms  chunk=${chunkCount}  content="${parsed.content ?? ""}"`,
                parsed
              );
            }

            if (parsed.reasoning_content !== undefined && parsed.reasoning_content !== "") {
              console.warn(
                `[STREAM] reasoning_content received (should be empty with thinking disabled): ${String(parsed.reasoning_content).slice(0, 200)}...`
              );
            }

            if (parsed.content) {
              onChunk(parsed.content);
              setState((s) => ({
                ...s,
                currentContent: s.currentContent + parsed.content,
              }));
            }
          }
        }

        console.log(
          `[STREAM] DONE  total_chunks=${chunkCount}  elapsed=${Date.now() - startTime}ms  first_chunk=${firstChunkTime !== null ? firstChunkTime - startTime : "N/A"}ms`
        );
        setState({ isStreaming: false, error: null, currentContent: "" });
        onDone();
      } catch (err: unknown) {
        if (err instanceof Error && err.name === "AbortError") {
          console.log("[STREAM] Aborted");
          setState({ isStreaming: false, error: null, currentContent: "" });
          return;
        }

        const message =
          err instanceof Error
            ? err.message
            : "流式响应失败，请检查网络或重试";
        console.error(`[STREAM] ERROR: ${message}  elapsed=${Date.now() - startTime}ms  chunks_received=${chunkCount}`);
        setState({ isStreaming: false, error: message, currentContent: "" });
        onError(message);
      } finally {
        abortControllerRef.current = null;
        if (timeoutRef.current) clearTimeout(timeoutRef.current);
      }
    },
    []
  );

  const cancelStream = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setState({ isStreaming: false, error: null, currentContent: "" });
  }, []);

  return { ...state, startStream, cancelStream };
}
