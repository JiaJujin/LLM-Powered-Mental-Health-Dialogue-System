import { BadgeHelp } from "lucide-react";

interface Props {
  highlighted?: boolean;
}

export default function HumanSupportCard({ highlighted }: Props) {
  return (
    <div className={`card support-card ${highlighted ? "warning" : ""}`}>
      <div className="card-title with-icon">
        <BadgeHelp size={18} />
        <span>Need Human Support?</span>
      </div>

      <p className="card-text">
        While AI insights are helpful, sometimes talking to a real person makes all the
        difference. Connect with counsellors, social workers, writers, and peer supporters
        who are here to help.
      </p>

      <button className="dark-btn">Connect with Helpers</button>
    </div>
  );
}
