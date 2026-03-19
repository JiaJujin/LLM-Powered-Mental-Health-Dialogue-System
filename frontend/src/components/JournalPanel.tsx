import { useState, useRef, useEffect } from "react";
import { BookOpen, ChevronDown, ChevronLeft, ChevronRight, Calendar, X } from "lucide-react";
import type { JournalResponse, JournalEntryResponse } from "../types";
import ConversationView from "./ConversationView";

interface Props {
  onSubmit: (payload: {
    content: string;
    mood?: string;
    weather?: string;
    title?: string;
    entry_date?: string;
  }) => Promise<void> | void;
  lastResult: JournalResponse | null;
  anonId: string;
  onHistoryClick: () => void;
  selectedEntry: JournalEntryResponse | null;
  onClearSelection: () => void;
}

// Mood options with emoji
const MOOD_OPTIONS = [
  { value: "Happy", label: "😊 Happy" },
  { value: "Calm", label: "😌 Calm" },
  { value: "Angry", label: "😠 Angry" },
  { value: "Anxious", label: "😰 Anxious" },
  { value: "Sad", label: "😢 Sad" },
  { value: "Excited", label: "🤩 Excited" },
  { value: "Grateful", label: "🙏 Grateful" },
];

// Weather options with emoji
const WEATHER_OPTIONS = [
  { value: "Warm", label: "☀️ Warm" },
  { value: "Hot", label: "🔥 Hot" },
  { value: "Cold", label: "🥶 Cold" },
  { value: "Cloudy", label: "☁️ Cloudy" },
  { value: "Rainy", label: "🌧️ Rainy" },
  { value: "Snowy", label: "❄️ Snowy" },
  { value: "Cool", label: "🌬️ Cool" },
];

// Reusable styled dropdown component
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

// Full Calendar Date Picker Component
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
    const daysInMonth = lastDay.getDate();
    const startingDay = firstDay.getDay();
    return { daysInMonth, startingDay };
  };

  const { daysInMonth, startingDay } = getDaysInMonth(viewDate);
  const monthNames = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
  ];
  const dayNames = ["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"];

  const goToPrevMonth = () => {
    setViewDate(new Date(viewDate.getFullYear(), viewDate.getMonth() - 1, 1));
  };

  const goToNextMonth = () => {
    setViewDate(new Date(viewDate.getFullYear(), viewDate.getMonth() + 1, 1));
  };

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
            {/* Empty cells for days before the first of month */}
            {Array.from({ length: startingDay }).map((_, i) => (
              <div key={`empty-${i}`} className="calendar-day empty" />
            ))}
            {/* Days of the month */}
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

export default function JournalPanel({
  onSubmit,
  lastResult,
  anonId,
  onHistoryClick,
  selectedEntry,
  onClearSelection,
}: Props) {
  const [content, setContent] = useState("");
  const [title, setTitle] = useState("");
  const [mood, setMood] = useState("");
  const [weather, setWeather] = useState("");
  const [entryDate, setEntryDate] = useState(
    new Date().toISOString().split("T")[0]
  );
  const [loading, setLoading] = useState(false);

  // If viewing a selected entry (from history), show read-only mode
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
                    weekday: "long",
                    month: "long",
                    day: "numeric",
                    year: "numeric",
                  })
                : new Date(selectedEntry.created_at).toLocaleDateString("en-US", {
                    weekday: "long",
                    month: "long",
                    day: "numeric",
                    year: "numeric",
                  })}
            </span>
            {selectedEntry.mood && <span className="entry-mood">{selectedEntry.mood}</span>}
            {selectedEntry.weather && <span className="entry-weather">{selectedEntry.weather}</span>}
          </div>

          {selectedEntry.title && <h3 className="entry-title">{selectedEntry.title}</h3>}

          <div className="entry-content">{selectedEntry.content}</div>
        </div>
      </div>
    );
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!content.trim()) return;

    setLoading(true);
    try {
      await onSubmit({
        content,
        mood,
        weather,
        title: title || undefined,
        entry_date: entryDate,
      });
      // Clear form after successful submission
      setContent("");
      setTitle("");
      setMood("");
      setWeather("");
      setEntryDate(new Date().toISOString().split("T")[0]);
    } finally {
      setLoading(false);
    }
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
        <button className="btn-past-entries" onClick={onHistoryClick}>
          Past Entries
        </button>
      </div>

      <form className="journal-form" onSubmit={handleSubmit}>
        {/* Date and Title Row */}
        <div className="input-row two-col date-title-row">
          <CalendarDatePicker
            label="Date"
            value={entryDate}
            onChange={setEntryDate}
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

        {/* Journal Content */}
        <div className="input-group content-group">
          <label className="input-label">Write your thoughts</label>
          <div className="textarea-wrapper">
            <textarea
              className="journal-textarea"
              value={content}
              onChange={(e) => setContent(e.target.value)}
              placeholder="What's on your mind?"
              rows={12}
            />
          </div>
        </div>

        {/* Action Buttons */}
        <div className="form-actions">
          <button
            type="button"
            className="btn-secondary"
            onClick={handleSaveDraft}
          >
            Save Draft
          </button>
          <button
            type="submit"
            className="btn-primary"
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
