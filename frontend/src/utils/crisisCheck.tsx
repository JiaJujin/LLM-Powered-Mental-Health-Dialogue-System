/**
 * Crisis check utility — calls the backend /api/crisis/alerts endpoint
 * and shows a non-dismissible modal when a crisis is detected.
 *
 * Usage:
 *   import { checkAndReportCrisis } from "./crisisCheck";
 *   checkAndReportCrisis(text, "diary", userId);
 */

import { createRoot } from "react-dom/client";

// ---------------------------------------------------------------------------
// Modal component (rendered via portal so it sits above everything)
// ---------------------------------------------------------------------------

function CrisisModal({ onClose }: { onClose: () => void }) {
  return (
    <div className="crisis-modal-overlay" role="dialog" aria-modal="true" aria-labelledby="crisis-modal-title">
      <div className="crisis-modal-card">
        <div className="crisis-modal-icon" aria-hidden="true">
          <svg width="48" height="48" viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
            <circle cx="24" cy="24" r="24" fill="#FEF2F2" />
            <path d="M24 12C18.477 12 14 16.477 14 22c0 6.5 10 18 10 18s10-11.5 10-18c0-5.523-4.477-10-10-10z" fill="#EF4444"/>
            <circle cx="24" cy="22" r="3" fill="#EF4444"/>
            <path d="M24 30v3" stroke="#EF4444" strokeWidth="2.5" strokeLinecap="round"/>
          </svg>
        </div>

        <h2 className="crisis-modal-title" id="crisis-modal-title">
          We're Here for You
        </h2>

        <p className="crisis-modal-body">
          We noticed something in your message that concerns us.
          A counselor has been notified and will follow up with you.
          If you need immediate help, please call the&nbsp;
          <strong>Samaritan Befrienders Hong Kong: 2382 0000</strong>
        </p>

        <button
          type="button"
          className="crisis-modal-btn"
          onClick={onClose}
        >
          I Understand
        </button>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Singleton state — only one modal can be open at a time
// ---------------------------------------------------------------------------

let activeRoot: ReturnType<typeof createRoot> | null = null;
let activeContainer: HTMLDivElement | null = null;
let dismissTimer: ReturnType<typeof setTimeout> | null = null;

/** Guards against stacking / rapid re-trigger within 60 seconds */
function isRecentlyDismissed(): boolean {
  return dismissTimer !== null;
}

function showCrisisModal() {
  if (activeRoot) return;          // already showing
  if (isRecentlyDismissed()) return; // re-trigger guard

  // Start 60-second cooldown
  dismissTimer = setTimeout(() => {
    dismissTimer = null;
  }, 60_000);

  const container = document.createElement("div");
  document.body.appendChild(container);
  activeContainer = container;

  const close = () => {
    if (activeRoot) {
      activeRoot.unmount();
      activeRoot = null;
    }
    if (activeContainer) {
      document.body.removeChild(activeContainer);
      activeContainer = null;
    }
  };

  activeRoot = createRoot(container);
  activeRoot.render(<CrisisModal onClose={close} />);
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/**
 * Fires the crisis check POST to /api/crisis/alerts.
 * Shows a non-dismissible modal if the backend reports crisis_detected=true.
 * Silently fails — the user is never blocked by a network or parse error.
 */
export async function checkAndReportCrisis(
  text: string,
  source: "diary" | "chat",
  userId: string
): Promise<void> {
  try {
    const payload = { user_id: userId, source, text };
    console.log("[CRISIS] POST /api/crisis/alerts  payload:", payload);
    const res = await fetch("/api/crisis/alerts", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    console.log("[CRISIS] response  status:", res.status);
    if (!res.ok) return;
    const data: { crisis_detected: boolean } = await res.json();
    console.log("[CRISIS] response JSON:", data);
    if (data.crisis_detected) {
      showCrisisModal();
    }
  } catch (err) {
    console.error("[CRISIS] fetch error:", err);
  }
}
