import { Heart } from "lucide-react";
import type { PrecheckResponse } from "../types";

interface Props {
  precheckResult: PrecheckResponse | null;
  onChangeCheckin: () => void;
}

export default function PrecheckStatusBar({ 
  precheckResult, 
  onChangeCheckin 
}: Props) {
  const mode = precheckResult?.role || "Not set";

  return (
    <div className="precheck-status-bar">
      <div className="status-left">
        <Heart size={16} className="status-icon" />
        <span className="status-label">Current support mode:</span>
        <span className="status-mode">{mode}</span>
      </div>
      <button 
        className="btn-change-checkin" 
        onClick={onChangeCheckin}
      >
        Change check-in
      </button>
    </div>
  );
}
