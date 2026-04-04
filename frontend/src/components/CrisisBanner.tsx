/**
 * CrisisBanner — gentle bottom-of-screen notification shown to the user
 * when LLM-based crisis detection triggers on diary or chat input.
 *
 * Auto-dismisses after 10 seconds (handled by the parent via useEffect).
 * Can be manually dismissed via the ✕ button.
 */

import { ASSIGNED_SUPPORTER } from "../utils/mockSupporter";

interface CrisisBannerProps {
  onDismiss: () => void;
}

export default function CrisisBanner({ onDismiss }: CrisisBannerProps) {
  return (
    <div className="crisis-banner" role="alert" aria-live="polite">
      <span className="crisis-banner__icon" aria-hidden="true">
        💛
      </span>
      <p className="crisis-banner__text">
        We noticed you may be going through something difficult.
        Your helper <strong>{ASSIGNED_SUPPORTER.name}</strong> has been notified.
      </p>
      <button
        type="button"
        className="crisis-banner__close"
        onClick={onDismiss}
        aria-label="Dismiss notification"
      >
        ✕
      </button>
    </div>
  );
}
