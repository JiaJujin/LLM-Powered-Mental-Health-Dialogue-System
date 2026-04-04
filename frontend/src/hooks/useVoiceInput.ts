/**
 * useVoiceInput — shared voice recording hook
 *
 * Features:
 * - Push-to-talk: continuous=true so browser never auto-stops on silence
 * - Auto-restart on silence: when browser stops recognition due to quiet,
 *   the onend handler re-starts it as long as the user hasn't manually stopped
 * - Live interim display (gray, updating in real-time)
 * - Final transcript chunks accumulated across all speech segments;
 *   onFinal fires when user manually stops recording
 * - Backend STT fallback (Whisper / Google auto-detect)
 *
 * Key mechanism: isRecordingRef prevents stale-closure bugs.
 * onend checks isRecordingRef BEFORE restarting so that a manual stop()
 * call (which also fires onend) correctly skips the restart.
 *
 * Usage:
 *   const { isRecording, isTranscribing, interimTranscript, error, recordingTime, toggleRecording } =
 *     useVoiceInput({ onFinal: (text) => setInput((p) => p + text) });
 */

import { useState, useRef, useCallback, useEffect } from "react";
import { transcribeAudio } from "../api";

export interface UseVoiceInputOptions {
  /** Called with the accumulated final transcript when the user manually stops recording */
  onFinal: (text: string) => void;
  /** Called when an error occurs */
  onError?: (message: string) => void;
}

export interface UseVoiceInputReturn {
  isRecording: boolean;
  isTranscribing: boolean;
  /** Live interim transcript (gray, spoken right now) */
  interimTranscript: string;
  /** Accumulated final transcripts so far (solid text from completed speech segments) */
  accumulatedTranscript: string;
  recordingTime: number;
  error: string | null;
  /** Call to start recording (first click) or stop recording (second click) */
  toggleRecording: () => void;
}

export function useVoiceInput({
  onFinal,
  onError,
}: UseVoiceInputOptions): UseVoiceInputReturn {
  const [isRecording, setIsRecording] = useState(false);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [interimTranscript, setInterimTranscript] = useState("");
  const [accumulatedTranscript, setAccumulatedTranscript] = useState("");
  const [recordingTime, setRecordingTime] = useState(0);
  const [error, setError] = useState<string | null>(null);

  // CRITICAL: useRef, not useState, to avoid stale closure in onend
  // true  = user has clicked start, hasn't clicked stop yet
  // false = user hasn't started, OR has clicked stop
  const isRecordingRef = useRef(false);

  // Accumulated final transcript across all speech segments
  const accumulatedFinalRef = useRef("");

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const srRef = useRef<any>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  // ---- Cleanup on unmount ----
  useEffect(() => {
    return () => {
      isRecordingRef.current = false;
      if (timerRef.current) clearInterval(timerRef.current);
      if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
        mediaRecorderRef.current.stop();
      }
      if (srRef.current) {
        try { srRef.current.stop(); } catch { /* ignore */ }
      }
    };
  }, []);

  // ---- Web Speech API (continuous=true, interimResults=true) ----
  const buildRecognition = useCallback(() => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const SR = ((window as unknown as Record<string, unknown>)["SpeechRecognition"] as any)
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      ?? ((window as unknown as Record<string, unknown>)["webkitSpeechRecognition"] as any);

    if (!SR) {
      setError("Please use Chrome or Edge for voice input.");
      return null;
    }

    const sr = new SR();
    sr.continuous = true;       // do NOT stop on silence — push-to-talk
    sr.interimResults = true;   // live interim display
    sr.maxAlternatives = 1;     // one best guess per result
    sr.lang = "";               // browser/system auto-detect (Cantonese, Mandarin, English, etc.)

    // ---- onstart: recognition has begun ----
    sr.onstart = () => {
      console.log("[VOICE] onstart");
    };

    // ---- onresult: accumulate finals, update interim in real-time ----
    //
    // CRITICAL: start from event.resultIndex, NOT 0.
    // The SpeechRecognition API re-emits ALL results on each event (even after
    // a silence-triggered restart). Starting from resultIndex ensures we only
    // process NEW results, preventing duplication (e.g. "你好。你好。你好。").
    //
    // - event.resultIndex = index of the FIRST new result in this event batch
    // - results before resultIndex were already processed in a prior event
    // - isFinal=true → browser has committed this phrase → safe to append
    // - isFinal=false (interim) → replaced each time, never duplicated
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    sr.onresult = (event: any) => {
      let newInterim = "";
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const t = event.results[i];
        const text = t[0].transcript;
        if (t.isFinal) {
          console.log(`[VOICE] result final=${text}`);
          // New confirmed phrase — append to persistent ref
          accumulatedFinalRef.current += text;
          // Mirror to UI state so the textarea shows solid text immediately
          setAccumulatedTranscript((prev) => prev + text);
        } else {
          console.log(`[VOICE] result interim=${text}`);
          newInterim += text;
        }
      }
      // Interim is replaced entirely each event (never accumulated); it shows
      // gray live text for whatever is being said right now
      setInterimTranscript(newInterim);
    };

    // ---- onerror: ignore no-speech (silence causes this, not an error) ----
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    sr.onerror = (event: any) => {
      console.log(`[VOICE] onerror ${event.error}`);
      if (event.error === "no-speech") return;
      const msg = `Voice error (${event.error}). Please try again.`;
      setError(msg);
      onError?.(msg);
      isRecordingRef.current = false;
      setIsRecording(false);
      if (timerRef.current) { clearInterval(timerRef.current); timerRef.current = null; }
    };

    // ---- onend: auto-restart ONLY if user hasn't manually stopped ----
    sr.onend = () => {
      console.log("[VOICE] onend");
      if (isRecordingRef.current) {
        // Browser stopped due to silence — restart immediately so recording continues
        try {
          sr.start();
        } catch {
          // "already started" errors are expected; ignore
        }
      } else {
      // User clicked stop → fire onFinal with everything we accumulated
      if (timerRef.current) { clearInterval(timerRef.current); timerRef.current = null; }
      if (srRef.current) { srRef.current = null; }
      setIsRecording(false);
      setRecordingTime(0);

      const finalText = accumulatedFinalRef.current.trim();
      accumulatedFinalRef.current = "";
      setInterimTranscript("");
      setAccumulatedTranscript("");

        if (finalText) {
          onFinal(finalText);
        } else {
          setError("No speech detected. Please try again.");
          onError?.("No speech detected. Please try again.");
        }
      }
    };

    return sr;
  }, [onFinal, onError]);

  const startWebSpeech = useCallback(() => {
    const sr = buildRecognition();
    if (!sr) return false;

    try {
      console.log("[VOICE] start called");
      sr.start();
    } catch {
      setError("Failed to start voice recognition. Please try again.");
      return false;
    }

    srRef.current = sr;
    return true;
  }, [buildRecognition]);

  // ---- Backend STT fallback ----
  const stopBackendSTT = useCallback(
    async (blob: Blob, mimeType: string) => {
      setIsTranscribing(true);
      setInterimTranscript("");
      try {
        const result = await transcribeAudio(
          blob,
          `voice_${Date.now()}.${mimeType.includes("webm") ? "webm" : "mp4"}`
        );
        const text = result.transcript || "";
        if (text.trim()) {
          onFinal(text.trim());
        } else {
          const msg = "No speech detected. Please try again.";
          setError(msg);
          onError?.(msg);
        }
      } catch {
        const msg = "Voice service unavailable. Please use Chrome or Edge for voice input.";
        setError(msg);
        onError?.(msg);
      } finally {
        setIsTranscribing(false);
        setRecordingTime(0);
      }
    },
    [onFinal, onError]
  );

  // ---- Main toggle handler ----
  const toggleRecording = useCallback(async () => {
    setError(null);
    setInterimTranscript("");
    console.log("[VOICE] mic clicked");

    if (isRecording || isTranscribing) {
      // ---- User wants to stop ----
      // Update UI state IMMEDIATELY so the mic button switches icon without delay
      setIsRecording(false);
      setRecordingTime(0);
      if (timerRef.current) { clearInterval(timerRef.current); timerRef.current = null; }

      // Set ref BEFORE abort so onend skips auto-restart
      isRecordingRef.current = false;

      // Stop Web Speech API with abort() — stops listening immediately,
      // does NOT wait for a final result, and does NOT fire onresult.
      // This is the key fix: stop() waits and feels sluggish.
      if (srRef.current) {
        try {
          console.log("[VOICE] abort called");
          srRef.current.abort();
        } catch { /* ignore */ }
        srRef.current = null;
      }

      // Stop MediaRecorder fallback
      if (
        mediaRecorderRef.current &&
        mediaRecorderRef.current.state !== "inactive"
      ) {
        mediaRecorderRef.current.stop();
        // onstop will fire async → stopBackendSTT
      }
      return;
    }

    // ---- User wants to start ----
    accumulatedFinalRef.current = "";
    setAccumulatedTranscript("");
    isRecordingRef.current = true;
    setRecordingTime(0);

    // 1. Try Web Speech API first (live interim display + auto-restart)
    const wsOk = startWebSpeech();
    if (wsOk) {
      setIsRecording(true);
      timerRef.current = setInterval(() => setRecordingTime((t) => t + 1), 1000);
      return;
    }

    // 2. Fall back to MediaRecorder + backend STT
    try {
      chunksRef.current = [];
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mimeType = MediaRecorder.isTypeSupported("audio/webm")
        ? "audio/webm"
        : "audio/mp4";
      const mediaRecorder = new MediaRecorder(stream, { mimeType });
      mediaRecorderRef.current = mediaRecorder;

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };

      mediaRecorder.onstop = () => {
        stream.getTracks().forEach((t) => t.stop());
        const blob = new Blob(chunksRef.current, { type: mimeType });
        isRecordingRef.current = false;
        stopBackendSTT(blob, mimeType);
      };

      mediaRecorder.start(1000);
      setIsRecording(true);
      timerRef.current = setInterval(() => setRecordingTime((t) => t + 1), 1000);
    } catch (err) {
      isRecordingRef.current = false;
      const e = err as Error;
      if (e.name === "NotAllowedError") {
        const msg = "Please allow microphone access in your browser settings.";
        setError(msg);
        onError?.(msg);
      } else {
        const msg = `Microphone error: ${e.message}`;
        setError(msg);
        onError?.(msg);
      }
    }
  }, [isRecording, isTranscribing, startWebSpeech, stopBackendSTT, onError]);

  return {
    isRecording,
    isTranscribing,
    interimTranscript,
    accumulatedTranscript,
    recordingTime,
    error,
    toggleRecording,
  };
}
