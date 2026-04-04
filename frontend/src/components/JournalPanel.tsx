import { useState, useRef, useEffect } from "react";
import {
  BookOpen,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  Calendar,
  X,
  Mic,
  MicOff,
  Paperclip,
  ImageIcon,
  RotateCcw,
  CheckCircle2,
} from "lucide-react";
import type { JournalEntryResponse } from "../types";
import { ocrDiaryImage, fetchTodayJournalEntry } from "../api";
import { useVoiceInput } from "../hooks/useVoiceInput";
import { checkAndReportCrisis } from "../utils/crisisCheck";
import ConversationView from "./ConversationView";

// -----------------------------------------------------------------------
// Mood & Weather Options
// -----------------------------------------------------------------------
const MOOD_OPTIONS = [
  { value: "Happy", label: "😊 Happy" },
  { value: "Calm", label: "😌 Calm" },
  { value: "Angry", label: "😠 Angry" },
  { value: "Anxious", label: "😰 Anxious" },
  { value: "Sad", label: "😢 Sad" },
  { value: "Excited", label: "🤩 Excited" },
  { value: "Grateful", label: "🙏 Grateful" },
];

const WEATHER_OPTIONS = [
  { value: "Warm", label: "☀️ Warm" },
  { value: "Hot", label: "🔥 Hot" },
  { value: "Cold", label: "🥶 Cold" },
  { value: "Cloudy", label: "☁️ Cloudy" },
  { value: "Rainy", label: "🌧️ Rainy" },
  { value: "Snowy", label: "❄️ Snowy" },
  { value: "Cool", label: "🌬️ Cool" },
];

// -----------------------------------------------------------------------
// Styled Select Dropdown
// -----------------------------------------------------------------------
function StyledSelect({
  value,
  onChange,
  options,
  placeholder,
  label,
}: {
  value: string;
  onChange: (value: string) => void;
  options: { value: string; label: string }[];
  placeholder: string;
  label: string;
}) {
  const [isOpen, setIsOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (ref.current && !ref.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const selectedOption = options.find((opt) => opt.value === value);

  return (
    <div className="styled-select-wrapper" ref={ref}>
      <label className="input-label">{label}</label>
      <button
        type="button"
        className={`styled-select-trigger ${isOpen ? "open" : ""} ${value ? "has-value" : ""}`}
        onClick={() => setIsOpen(!isOpen)}
      >
        <span>{selectedOption?.label || placeholder}</span>
        <ChevronDown size={16} className="chevron" />
      </button>
      {isOpen && (
        <div className="styled-select-dropdown">
          {options.map((option) => (
            <button
              key={option.value}
              type="button"
              className={`styled-select-option ${option.value === value ? "selected" : ""}`}
              onClick={() => {
                onChange(option.value);
                setIsOpen(false);
              }}
            >
              {option.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

// -----------------------------------------------------------------------
// Calendar Date Picker
// -----------------------------------------------------------------------
function CalendarDatePicker({
  value,
  onChange,
  label,
}: {
  value: string;
  onChange: (value: string) => void;
  label: string;
}) {
  const [isOpen, setIsOpen] = useState(false);
  const [viewDate, setViewDate] = useState(value ? new Date(value) : new Date());
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (ref.current && !ref.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const formatDisplayDate = (dateStr: string) => {
    if (!dateStr) return "";
    const date = new Date(dateStr);
    return date.toLocaleDateString("en-US", {
      weekday: "long",
      month: "long",
      day: "numeric",
      year: "numeric",
    });
  };

  const getDaysInMonth = (date: Date) => {
    const year = date.getFullYear();
    const month = date.getMonth();
    const firstDay = new Date(year, month, 1);
    const lastDay = new Date(year, month + 1, 0);
    return { daysInMonth: lastDay.getDate(), startingDay: firstDay.getDay() };
  };

  const { daysInMonth, startingDay } = getDaysInMonth(viewDate);
  const monthNames = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
  ];
  const dayNames = ["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"];

  const goToPrevMonth = () => setViewDate(new Date(viewDate.getFullYear(), viewDate.getMonth() - 1, 1));
  const goToNextMonth = () => setViewDate(new Date(viewDate.getFullYear(), viewDate.getMonth() + 1, 1));

  const handleDateSelect = (day: number) => {
    const selectedDate = new Date(viewDate.getFullYear(), viewDate.getMonth(), day);
    onChange(selectedDate.toISOString().split("T")[0]);
    setIsOpen(false);
  };

  const selectedDate = value ? new Date(value) : null;

  return (
    <div className="calendar-picker-wrapper" ref={ref}>
      <label className="input-label">{label}</label>
      <button
        type="button"
        className={`calendar-picker-trigger ${isOpen ? "open" : ""} ${value ? "has-value" : ""}`}
        onClick={() => setIsOpen(!isOpen)}
      >
        <Calendar size={16} className="calendar-icon" />
        <span>{value ? formatDisplayDate(value) : "Select date"}</span>
        <ChevronDown size={16} className="chevron" />
      </button>

      {isOpen && (
        <div className="calendar-picker-dropdown">
          <div className="calendar-header">
            <button type="button" className="calendar-nav-btn" onClick={goToPrevMonth}>
              <ChevronLeft size={18} />
            </button>
            <span className="calendar-month-year">
              {monthNames[viewDate.getMonth()]} {viewDate.getFullYear()}
            </span>
            <button type="button" className="calendar-nav-btn" onClick={goToNextMonth}>
              <ChevronRight size={18} />
            </button>
          </div>

          <div className="calendar-weekdays">
            {dayNames.map((day) => (
              <div key={day} className="calendar-weekday">{day}</div>
            ))}
          </div>

          <div className="calendar-days">
            {Array.from({ length: startingDay }).map((_, i) => (
              <div key={`empty-${i}`} className="calendar-day empty" />
            ))}
            {Array.from({ length: daysInMonth }).map((_, i) => {
              const day = i + 1;
              const currentDate = new Date(viewDate.getFullYear(), viewDate.getMonth(), day);
              const dateStr = currentDate.toISOString().split("T")[0];
              const isSelected = selectedDate && selectedDate.toISOString().split("T")[0] === dateStr;
              const isToday = new Date().toISOString().split("T")[0] === dateStr;

              return (
                <button
                  key={day}
                  type="button"
                  className={`calendar-day ${isSelected ? "selected" : ""} ${isToday ? "today" : ""}`}
                  onClick={() => handleDateSelect(day)}
                >
                  {day}
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

// -----------------------------------------------------------------------
// Voice Input inline (using shared hook)
// -----------------------------------------------------------------------
function VoiceInputInline({
  isRecording,
  isTranscribing,
  interimTranscript,
  error,
  onToggle,
}: {
  isRecording: boolean;
  isTranscribing: boolean;
  interimTranscript: string;
  error: string | null;
  onToggle: () => void;
}) {
  return (
    <>
      <button
        type="button"
        className={`toolbar-btn mic-btn ${isRecording ? "recording" : ""} ${isTranscribing ? "transcribing" : ""}`}
        title={isRecording ? "Stop recording" : "Start voice recording"}
        onClick={onToggle}
        disabled={isTranscribing}
      >
        {isRecording || isTranscribing ? (
          <span className="mic-icon-wrapper">
            <MicOff size={20} />
            {isRecording && <span className="recording-dot" />}
          </span>
        ) : (
          <Mic size={20} />
        )}
      </button>
      {error && <div className="input-error">{error}</div>}
    </>
  );
}

// -----------------------------------------------------------------------
// Main JournalPanel Component
// -----------------------------------------------------------------------
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
    title?: string;
    entry_date?: string;
  }) => Promise<void> | void;
  onSubmitWithMeta?: (payload: {
    content: string;
    mood?: string;
    weather?: string;
    title?: string;
    entry_date?: string;
    source_type: "text" | "voice" | "image";
    original_input_text: string;
    source_file_path?: string;
    input_metadata?: Record<string, unknown>;
  }) => Promise<void> | void;
  lastResult: import("../types").JournalResponse | null;
  anonId: string;
  onHistoryClick: () => void;
  selectedEntry: JournalEntryResponse | null;
  onClearSelection: () => void;
  /** Today's date string (YYYY-MM-DD) — used to fetch existing entry on mount */
  today?: string;
  /** External date signal: when set, load entry for that date */
  writeDate?: string;
  onClearWriteDate?: () => void;
}

export default function JournalPanel({
  onSubmit,
  onSubmitWithMeta,
  lastResult,
  anonId,
  onHistoryClick,
  selectedEntry,
  onClearSelection,
  today = new Date().toISOString().split("T")[0],
  writeDate,
  onClearWriteDate,
}: Props) {
  const [content, setContent] = useState("");
  const [title, setTitle] = useState("");
  const [mood, setMood] = useState("");
  const [weather, setWeather] = useState("");
  const [entryDate, setEntryDate] = useState(
    new Date().toISOString().split("T")[0]
  );
  const [loading, setLoading] = useState(false);
  const [draftMeta, setDraftMeta] = useState<Partial<SubmitMeta>>({});
  const [showSavedToast, setShowSavedToast] = useState(false);
  const [isViewingPastEntry, setIsViewingPastEntry] = useState(false);

  // ---- Image preview state ----
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [imageName, setImageName] = useState<string>("");
  const [ocring, setOcring] = useState(false);
  const [ocrError, setOcrError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

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
      const newContent = content.trim() ? `${content.trim()}\n${text}` : text;
      setContent(newContent);
      setDraftMeta({
        source_type: "voice",
        original_input_text: text,
        input_metadata: { source_type: "voice", backend: "webspeech" },
      });
    },
    onError: () => {},
  });

  // ---- Crisis detection: debounced check on textarea change ----
  const crisisDebounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    // Clean up any pending timer when content changes
    if (crisisDebounceRef.current) {
      clearTimeout(crisisDebounceRef.current);
    }
    // Only block completely empty input — allow short Chinese crisis phrases
    if (!content.trim()) return;

    crisisDebounceRef.current = setTimeout(() => {
      console.log("[CRISIS] diary sending", content);
      checkAndReportCrisis(content, "diary", anonId);
    }, 2000);

    return () => {
      if (crisisDebounceRef.current) {
        clearTimeout(crisisDebounceRef.current);
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [content, anonId]);

  // ---- Load today's existing entry on mount ----
  useEffect(() => {
    if (!anonId || !today) return;
    let cancelled = false;
    (async () => {
      const entry = await fetchTodayJournalEntry(anonId, today);
      if (cancelled) return;
      if (entry && entry.content) {
        setContent(entry.content);
        setTitle(entry.title ?? "");
        setMood(entry.mood ?? "");
        setWeather(entry.weather ?? "");
        if (entry.entry_date) setEntryDate(entry.entry_date);
      }
    })();
    return () => { cancelled = true; };
    // Only run once on mount — don't re-run when entryDate changes mid-session
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [anonId, today]);

  // ---- Load entry when writeDate (from History navigation) changes ----
  useEffect(() => {
    if (!writeDate) return;
    let cancelled = false;
    (async () => {
      const entry = await fetchTodayJournalEntry(anonId, writeDate);
      if (cancelled) return;
      setEntryDate(writeDate);
      if (entry && entry.content) {
        setContent(entry.content);
        setTitle(entry.title ?? "");
        setMood(entry.mood ?? "");
        setWeather(entry.weather ?? "");
        if (entry.entry_date) setEntryDate(entry.entry_date);
        setIsViewingPastEntry(writeDate !== new Date().toISOString().split("T")[0]);
      } else {
        // No entry for this date — clear form
        setContent("");
        setTitle("");
        setMood("");
        setWeather("");
        setDraftMeta({});
        removeImage();
        setIsViewingPastEntry(writeDate !== new Date().toISOString().split("T")[0]);
      }
    })();
    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [writeDate]);

  // Helper: load entry for a given date (used when user picks a date in the picker)
  const loadEntryForDate = async (date: string) => {
    let cancelled = false;
    const entry = await fetchTodayJournalEntry(anonId, date);
    if (cancelled) return;
    if (entry && entry.content) {
      setContent(entry.content);
      setTitle(entry.title ?? "");
      setMood(entry.mood ?? "");
      setWeather(entry.weather ?? "");
      if (entry.entry_date) setEntryDate(entry.entry_date);
      setIsViewingPastEntry(false);
    } else {
      setContent("");
      setTitle("");
      setMood("");
      setWeather("");
      setDraftMeta({});
      removeImage();
      setIsViewingPastEntry(date !== new Date().toISOString().split("T")[0]);
    }
  };

  // ---- Format time ----
  const formatTime = (seconds: number) => {
    const m = Math.floor(seconds / 60).toString().padStart(2, "0");
    const s = (seconds % 60).toString().padStart(2, "0");
    return `${m}:${s}`;
  };

  // ---- Image upload / OCR ----
  const processImage = async (file: File) => {
    if (!file.type.startsWith("image/")) {
      setOcrError("Please upload an image file (JPG, PNG, or WEBP).");
      return;
    }
    if (file.size > 10 * 1024 * 1024) {
      setOcrError("Image is too large. Maximum size is 10 MB.");
      return;
    }
    setOcrError(null);
    setImagePreview(URL.createObjectURL(file));
    setImageName(file.name);

    setOcring(true);
    try {
      const result = await ocrDiaryImage(file, file.name);
      const text = result.clean_text || result.raw_text || "";
      if (text.trim()) {
        const newContent = content.trim() ? `${content.trim()}\n${text}` : text;
        setContent(newContent);
        setDraftMeta({
          source_type: "image",
          original_input_text: result.raw_text || text,
          input_metadata: {
            source_type: "image",
            confidence: result.confidence,
            original_filename: file.name,
          },
        });
      } else {
        setOcrError("No text was detected in the image. You can describe the image manually in the text box.");
      }
    } catch {
      setOcrError("Image recognition is currently unavailable. You can describe the image manually in the text box.");
    } finally {
      setOcring(false);
    }
  };

  const handleImageFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) processImage(file);
  };

  const handleImageDrop = (e: React.DragEvent) => {
    e.preventDefault();
    const file = e.dataTransfer.files?.[0];
    if (file) processImage(file);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
  };

  const removeImage = () => {
    if (imagePreview) URL.revokeObjectURL(imagePreview);
    setImagePreview(null);
    setImageName("");
    setOcrError(null);
  };

  // ---- Cleanup on unmount ----
  useEffect(() => {
    return () => {
      if (imagePreview) URL.revokeObjectURL(imagePreview);
    };
  }, [imagePreview]);

  // ---- Read-only mode for selected entry ----
  if (selectedEntry) {
    return (
      <div className="journal-panel">
        <div className="journal-header">
          <div className="header-left">
            <BookOpen size={20} />
            <h2>View Entry</h2>
          </div>
          <button className="btn-close-view" onClick={onClearSelection}>
            <X size={20} />
          </button>
        </div>

        <div className="entry-view">
          <div className="entry-meta">
            <span className="entry-date">
              {selectedEntry.entry_date
                ? new Date(selectedEntry.entry_date).toLocaleDateString("en-US", {
                    weekday: "long", month: "long", day: "numeric", year: "numeric",
                  })
                : new Date(selectedEntry.created_at).toLocaleDateString("en-US", {
                    weekday: "long", month: "long", day: "numeric", year: "numeric",
                  })}
            </span>
            {selectedEntry.mood && <span className="entry-mood">{selectedEntry.mood}</span>}
            {selectedEntry.weather && <span className="entry-weather">{selectedEntry.weather}</span>}
            {selectedEntry.source_type && selectedEntry.source_type !== "text" && (
              <span className="entry-source-type">{selectedEntry.source_type}</span>
            )}
          </div>

          {selectedEntry.title && <h3 className="entry-title">{selectedEntry.title}</h3>}
          <div className="entry-content">{selectedEntry.content}</div>
        </div>
      </div>
    );
  }

  // ---- Submit ----
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!content.trim()) return;

    setLoading(true);
    try {
      if (onSubmitWithMeta && draftMeta.source_type && draftMeta.source_type !== "text") {
        await onSubmitWithMeta({
          content,
          mood,
          weather,
          title: title || undefined,
          entry_date: entryDate,
          source_type: draftMeta.source_type,
          original_input_text: draftMeta.original_input_text || content,
          source_file_path: draftMeta.source_file_path,
          input_metadata: draftMeta.input_metadata,
        });
      } else {
        await onSubmit({
          content,
          mood,
          weather,
          title: title || undefined,
          entry_date: entryDate,
        });
      }

      // Fire crisis check (non-blocking, silent on failure)
      console.log("[CRISIS] diary sending", content);
      checkAndReportCrisis(content, "diary", anonId);

      setShowSavedToast(true);
      setTimeout(() => setShowSavedToast(false), 2000);
      // If we were viewing a past entry, after saving switch back to today
      if (isViewingPastEntry) {
        setIsViewingPastEntry(false);
        setEntryDate(new Date().toISOString().split("T")[0]);
        setContent("");
        setTitle("");
        setMood("");
        setWeather("");
        setDraftMeta({});
        removeImage();
        onClearWriteDate?.();
      } else {
        // Reset form for new entry (today's date)
        setContent("");
        setTitle("");
        setMood("");
        setWeather("");
        setEntryDate(new Date().toISOString().split("T")[0]);
        setDraftMeta({});
        removeImage();
      }
    } finally {
      setLoading(false);
    }
  };

  const handleNewEntry = () => {
    setContent("");
    setTitle("");
    setMood("");
    setWeather("");
    setEntryDate(new Date().toISOString().split("T")[0]);
    setDraftMeta({});
    removeImage();
    setIsViewingPastEntry(false);
    onClearWriteDate?.();
  };

  const handleBackToToday = () => {
    setIsViewingPastEntry(false);
    setEntryDate(new Date().toISOString().split("T")[0]);
    setContent("");
    setTitle("");
    setMood("");
    setWeather("");
    setDraftMeta({});
    removeImage();
    onClearWriteDate?.();
  };

  const handleSaveDraft = () => {
    alert("Draft saved! (This feature is coming soon)");
  };

  return (
    <div className="journal-panel">
      <div className="journal-header">
        <div className="header-left">
          <BookOpen size={20} />
          <h2>New Entry</h2>
        </div>
        <div className="header-actions">
          <button className="btn-new-entry" onClick={handleNewEntry} title="Start a new entry for today">
            <RotateCcw size={14} />
            New Entry
          </button>
          <button className="btn-past-entries" onClick={onHistoryClick}>
            Past Entries
          </button>
        </div>
      </div>

      {isViewingPastEntry && (
        <div className="viewing-past-banner">
          <span>Viewing entry from {entryDate ? new Date(entryDate).toLocaleDateString("en-US", { month: "long", day: "numeric", year: "numeric" }) : ""}</span>
          <button className="btn-back-today" onClick={handleBackToToday}>
            Back to today
          </button>
        </div>
      )}

      {showSavedToast && (
        <div className="saved-toast">
          <CheckCircle2 size={16} />
          Entry saved
        </div>
      )}

      <form className="journal-form" onSubmit={handleSubmit}>
        {/* Date and Title Row */}
        <div className="input-row two-col date-title-row">
          <CalendarDatePicker
            label="Date"
            value={entryDate}
            onChange={loadEntryForDate}
          />
          <div className="input-group title-group">
            <label className="input-label">Title</label>
            <input
              type="text"
              className="title-input"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Entry title..."
            />
          </div>
        </div>

        {/* Mood and Weather Row */}
        <div className="input-row two-col">
          <StyledSelect
            label="Mood"
            value={mood}
            onChange={setMood}
            options={MOOD_OPTIONS}
            placeholder="How are you feeling?"
          />
          <StyledSelect
            label="Weather"
            value={weather}
            onChange={setWeather}
            options={WEATHER_OPTIONS}
            placeholder="How's the weather?"
          />
        </div>

        {/* Content Group */}
        <div className="input-group content-group">
          {/* Hidden file input */}
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            style={{ display: "none" }}
            onChange={handleImageFileChange}
            disabled={ocring}
          />

          {/* Image Preview (shown above textarea when image is loaded) */}
          {imagePreview && (
            <div
              className="image-preview-bar"
              onDrop={handleImageDrop}
              onDragOver={handleDragOver}
            >
              <div className="image-preview-thumb-wrapper">
                <img src={imagePreview} alt="Attached" className="image-preview-thumb" />
                <button
                  type="button"
                  className="image-remove-btn"
                  onClick={removeImage}
                  title="Remove image"
                >
                  <X size={12} />
                </button>
              </div>
              <span className="image-preview-filename">
                <ImageIcon size={14} />
                {imageName}
              </span>
            </div>
          )}

          {/* Textarea with live voice overlay */}
          <div className="textarea-wrapper">
            <div className="textarea-container">
              <textarea
                className="journal-textarea"
                value={isRecording ? accumulatedTranscript : content}
                onChange={(e) => setContent(e.target.value)}
                placeholder={
                  (isRecording || isTranscribing)
                    ? "Listening..."
                    : "What's on your mind?"
                }
                rows={12}
                disabled={isRecording}
              />
              {/* Live interim transcript overlay — shows gray interim above solid accumulated text */}
              {(isRecording || isTranscribing) && interimTranscript && (
                <div className="interim-overlay" aria-hidden="true">
                  <span className="interim-text">
                    {accumulatedTranscript ? `${accumulatedTranscript}\n` : ""}{interimTranscript}
                  </span>
                </div>
              )}
            </div>
          </div>

          {/* OCR loading */}
          {ocring && (
            <div className="transcribe-loading">
              <div className="spinner" />
              <span>Recognizing text in image...</span>
            </div>
          )}

          {/* OCR error */}
          {ocrError && (
            <div className="input-error">{ocrError}</div>
          )}

          {/* Voice loading (backend STT fallback) */}
          {isTranscribing && !isRecording && (
            <div className="transcribe-loading">
              <div className="spinner" />
              <span>Transcribing audio...</span>
            </div>
          )}

          {/* Voice error */}
          {voiceError && (
            <div className="input-error">{voiceError}</div>
          )}

          {/* ChatGPT-style bottom toolbar */}
          <div className="chatgpt-toolbar">
            {/* Left: attachment + mic buttons */}
            <div className="toolbar-left">
              <button
                type="button"
                className="toolbar-btn"
                title="Attach image"
                onClick={() => fileInputRef.current?.click()}
                disabled={ocring || isRecording || isTranscribing}
              >
                <Paperclip size={20} />
              </button>

              <VoiceInputInline
                isRecording={isRecording}
                isTranscribing={isTranscribing}
                interimTranscript={interimTranscript}
                error={null}
                onToggle={toggleRecording}
              />

              {(isRecording || isTranscribing) && (
                <span className="recording-timer">{formatTime(recordingTime)}</span>
              )}
            </div>

            {/* Right: placeholder spacer to keep left side aligned naturally */}
            <div style={{ flex: 1 }} />
          </div>
        </div>

        {/* Action Buttons — always visible at bottom */}
        <div className="form-actions-sticky">
          <button
            type="submit"
            className="btn-primary btn-save-fullwidth"
            disabled={loading || !content.trim()}
          >
            {loading ? "Analyzing..." : "Save & Analyze"}
          </button>
        </div>
      </form>

      {lastResult && (
        <div className="journal-result">
          <ConversationView data={lastResult} />
        </div>
      )}
    </div>
  );
}
