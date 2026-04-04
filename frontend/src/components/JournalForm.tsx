import { useState, useRef, useCallback, useEffect } from "react";
import { Mic, MicOff, Upload, ImageIcon, FileImage, BookOpen } from "lucide-react";
import { transcribeAudio, ocrDiaryImage } from "../api";
import type { JournalInputMode } from "../types";

interface SubmitMeta {
  source_type: "text" | "voice" | "image";
  original_input_text: string;
  source_file_path?: string;
  input_metadata: Record<string, unknown>;
}

interface Props {
  onSubmit: (payload: {
    content: string;
    mood?: string;
    weather?: string;
  }) => Promise<void> | void;
  onSubmitWithMeta?: (payload: {
    content: string;
    mood?: string;
    weather?: string;
    source_type: "text" | "voice" | "image";
    original_input_text: string;
    source_file_path?: string;
    input_metadata?: Record<string, unknown>;
  }) => Promise<void> | void;
  loading?: boolean;
}

// -----------------------------------------------------------------------
// Voice Input Panel
// -----------------------------------------------------------------------
function VoiceInputPanel({
  onDraftReady,
}: {
  onDraftReady: (text: string, meta: Partial<SubmitMeta>) => void;
}) {
  const [isRecording, setIsRecording] = useState(false);
  const [recordingTime, setRecordingTime] = useState(0);
  const [transcribing, setTranscribing] = useState(false);
  const [draftReady, setDraftReady] = useState(false);
  const [warnings, setWarnings] = useState<string[]>([]);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  const stopRecording = useCallback(() => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
      mediaRecorderRef.current.stop();
    }
    setIsRecording(false);
  }, []);

  const startRecording = async () => {
    try {
      setErrorMsg(null);
      setUploadError(null);
      setDraftReady(false);
      setWarnings([]);
      chunksRef.current = [];

      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: MediaRecorder.isTypeSupported("audio/webm") ? "audio/webm" : "audio/mp4",
      });
      mediaRecorderRef.current = mediaRecorder;

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };

      mediaRecorder.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop());
        const blob = new Blob(chunksRef.current, { type: mediaRecorder.mimeType });
        setTranscribing(true);
        try {
          const result = await transcribeAudio(blob, `voice_${Date.now()}.webm`);
          const text = result.transcript || "";
          setWarnings(result.warnings || []);
          if (text.trim()) {
            setDraftReady(true);
            onDraftReady(text, {
              source_type: "voice",
              original_input_text: text,
              input_metadata: {
                source_type: "voice",
                language: result.language,
                duration_seconds: result.duration_seconds,
              },
            });
          }
        } catch (err) {
          setUploadError(err instanceof Error ? err.message : "Transcription failed");
        } finally {
          setTranscribing(false);
        }
      };

      mediaRecorder.start(1000);
      setIsRecording(true);
      setRecordingTime(0);
      timerRef.current = setInterval(() => setRecordingTime((t) => t + 1), 1000);
    } catch (err) {
      if (err instanceof Error && err.name === "NotAllowedError") {
        setErrorMsg("Microphone access denied. Please allow microphone permissions.");
      } else {
        setErrorMsg("Could not access microphone.");
      }
    }
  };

  const handleAudioUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploadError(null);
    setDraftReady(false);
    setWarnings([]);
    setTranscribing(true);
    try {
      const result = await transcribeAudio(file, file.name);
      const text = result.transcript || "";
      setWarnings(result.warnings || []);
      if (text.trim()) {
        setDraftReady(true);
        onDraftReady(text, {
          source_type: "voice",
          original_input_text: text,
          input_metadata: {
            source_type: "voice",
            language: result.language,
            duration_seconds: result.duration_seconds,
            original_filename: file.name,
          },
        });
      }
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : "Transcription failed");
    } finally {
      setTranscribing(false);
    }
  };

  const formatTime = (seconds: number) =>
    `${Math.floor(seconds / 60).toString().padStart(2, "0")}:${(seconds % 60).toString().padStart(2, "0")}`;

  useEffect(() => {
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, []);

  return (
    <div className="voice-input-panel">
      <div className="voice-controls">
        <button
          type="button"
          className={`voice-btn ${isRecording ? "recording" : ""}`}
          onClick={isRecording ? stopRecording : startRecording}
          disabled={transcribing}
        >
          {isRecording ? <MicOff size={16} /> : <Mic size={16} />}
          {isRecording ? "Stop" : "Record"}
          {isRecording && <span className="recording-dot" />}
        </button>
        {isRecording && <span className="recording-timer">{formatTime(recordingTime)}</span>}
        <label className="voice-btn upload-btn" title="Upload audio">
          <Upload size={14} />
          <input type="file" accept="audio/*" style={{ display: "none" }} onChange={handleAudioUpload} disabled={transcribing} />
        </label>
      </div>
      {errorMsg && <div className="input-error">{errorMsg}</div>}
      {uploadError && <div className="input-error">{uploadError}</div>}
      {transcribing && <div className="transcribe-loading"><div className="spinner" /><span>Transcribing...</span></div>}
      {warnings.map((w, i) => <p key={i} className="warning-text">⚠️ {w}</p>)}
      {draftReady && <div className="draft-ready-banner">✅ Transcript ready — review and edit below</div>}
    </div>
  );
}

// -----------------------------------------------------------------------
// Image Input Panel
// -----------------------------------------------------------------------
function ImageInputPanel({
  onDraftReady,
}: {
  onDraftReady: (text: string, meta: Partial<SubmitMeta>) => void;
}) {
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [imageName, setImageName] = useState<string>("");
  const [ocring, setOcring] = useState(false);
  const [draftReady, setDraftReady] = useState(false);
  const [warnings, setWarnings] = useState<string[]>([]);
  const [ocrError, setOcrError] = useState<string | null>(null);
  const [isDragOver, setIsDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const processImage = async (file: File) => {
    if (!file.type.startsWith("image/") || file.size > 10 * 1024 * 1024) {
      setOcrError("Please upload a valid image (JPG/PNG/WEBP, max 10 MB).");
      return;
    }
    setOcrError(null);
    setDraftReady(false);
    setWarnings([]);
    const preview = URL.createObjectURL(file);
    setImagePreview(preview);
    setImageName(file.name);
    setOcring(true);
    try {
      const result = await ocrDiaryImage(file, file.name);
      const text = result.clean_text || result.raw_text || "";
      setWarnings(result.warnings || []);
      if (text.trim()) {
        setDraftReady(true);
        onDraftReady(text, {
          source_type: "image",
          original_input_text: result.raw_text || text,
          input_metadata: {
            source_type: "image",
            confidence: result.confidence,
            original_filename: file.name,
          },
        });
      }
    } catch (err) {
      setOcrError(err instanceof Error ? err.message : "OCR failed");
    } finally {
      setOcring(false);
    }
  };

  return (
    <div className="image-input-panel">
      <div
        className={`image-drop-zone ${isDragOver ? "drag-over" : ""} ${imagePreview ? "has-image" : ""}`}
        onDrop={(e) => { e.preventDefault(); setIsDragOver(false); processImage(e.dataTransfer.files[0]); }}
        onDragOver={(e) => { e.preventDefault(); setIsDragOver(true); }}
        onDragLeave={() => setIsDragOver(false)}
        onClick={() => fileInputRef.current?.click()}
      >
        <input ref={fileInputRef} type="file" accept="image/*" style={{ display: "none" }}
          onChange={(e) => { const f = e.target.files?.[0]; if (f) processImage(f); }} />
        {imagePreview ? (
          <div className="image-preview-container">
            <img src={imagePreview} alt="Preview" className="image-preview-thumb" />
            <div className="image-preview-info"><ImageIcon size={16} /><span>{imageName}</span></div>
          </div>
        ) : (
          <div className="drop-zone-placeholder"><FileImage size={28} /><p className="drop-title">Upload diary photo</p><p className="drop-hint">JPG, PNG, WEBP</p></div>
        )}
      </div>
      {ocrError && <div className="input-error">{ocrError}</div>}
      {ocring && <div className="transcribe-loading"><div className="spinner" /><span>Recognizing text...</span></div>}
      {warnings.map((w, i) => <p key={i} className="warning-text">⚠️ {w}</p>)}
      {draftReady && <div className="draft-ready-banner">✅ Text extracted — review and edit below</div>}
    </div>
  );
}

// -----------------------------------------------------------------------
// Input Mode Tabs
// -----------------------------------------------------------------------
const INPUT_MODE_TABS: { value: JournalInputMode; label: string; icon: React.ReactNode }[] = [
  { value: "text", label: "Text", icon: <BookOpen size={13} /> },
  { value: "voice", label: "Voice", icon: <Mic size={13} /> },
  { value: "image", label: "Image", icon: <ImageIcon size={13} /> },
];

function InputModeTabBar({ value, onChange }: { value: JournalInputMode; onChange: (m: JournalInputMode) => void }) {
  return (
    <div className="input-mode-tabs">
      {INPUT_MODE_TABS.map((tab) => (
        <button key={tab.value} type="button"
          className={`input-mode-tab ${value === tab.value ? "active" : ""}`}
          onClick={() => onChange(tab.value)}>
          {tab.icon}{tab.label}
        </button>
      ))}
    </div>
  );
}

// -----------------------------------------------------------------------
// JournalForm Component
// -----------------------------------------------------------------------
export default function JournalForm({ onSubmit, onSubmitWithMeta, loading = false }: Props) {
  const [content, setContent] = useState("");
  const [mood, setMood] = useState("");
  const [weather, setWeather] = useState("");
  const [inputMode, setInputMode] = useState<JournalInputMode>("text");
  const [draftMeta, setDraftMeta] = useState<Partial<SubmitMeta>>({});

  const handleDraftReady = useCallback((text: string, meta: Partial<SubmitMeta>) => {
    setContent(text);
    setDraftMeta(meta);
  }, []);

  const handleSubmit = async () => {
    if (!content.trim()) {
      alert("Please write some journal content first.");
      return;
    }
    if (onSubmitWithMeta && draftMeta.source_type && draftMeta.source_type !== "text") {
      await onSubmitWithMeta({
        content,
        mood,
        weather,
        source_type: draftMeta.source_type,
        original_input_text: draftMeta.original_input_text || content,
        source_file_path: draftMeta.source_file_path,
        input_metadata: draftMeta.input_metadata,
      });
    } else {
      await onSubmit({ content, mood, weather });
    }
  };

  const contentLabel = inputMode === "voice" ? "Voice transcript" : inputMode === "image" ? "OCR result" : "Journal entry";
  const placeholderText = inputMode === "voice"
    ? "Voice will be transcribed here..."
    : inputMode === "image"
    ? "Extracted text will appear here..."
    : "Write your journal here...";

  return (
    <div className="form-card">
      <div className="input-mode-tabs-row">
        <InputModeTabBar value={inputMode} onChange={setInputMode} />
      </div>

      {inputMode === "voice" && <VoiceInputPanel onDraftReady={handleDraftReady} />}
      {inputMode === "image" && <ImageInputPanel onDraftReady={handleDraftReady} />}

      <div className="form-grid two">
        <div className="field">
          <label>Mood</label>
          <input value={mood} onChange={(e) => setMood(e.target.value)} placeholder="e.g. tired, calm, confused" />
        </div>
        <div className="field">
          <label>Weather</label>
          <input value={weather} onChange={(e) => setWeather(e.target.value)} placeholder="e.g. rainy, sunny" />
        </div>
      </div>

      <div className="field">
        <label>{contentLabel}</label>
        <textarea
          value={content}
          onChange={(e) => setContent(e.target.value)}
          placeholder={placeholderText}
          rows={10}
        />
      </div>

      <button className="primary-btn" onClick={handleSubmit} disabled={loading}>
        {loading ? "Analyzing..." : "Save & Analyze"}
      </button>
    </div>
  );
}
