import type { CrisisResult } from "../types";

interface Props {
  risk: CrisisResult;
}

export default function RiskBanner({ risk }: Props) {
  const isHigh = risk.risk_level >= 3;
  const isMedium = risk.risk_level === 2;

  return (
    <div className={`risk-banner ${isHigh ? "high" : isMedium ? "medium" : "low"}`}>
      <div className="risk-title">
        Risk Level {risk.risk_level}
      </div>

      <p>{risk.trigger}</p>

      {risk.evidence.length > 0 && (
        <ul>
          {risk.evidence.map((item, idx) => (
            <li key={idx}>{item}</li>
          ))}
        </ul>
      )}

      {isHigh && (
        <div className="risk-help">
          Please consider reaching out to a real person immediately or local crisis support.
        </div>
      )}
    </div>
  );
}
