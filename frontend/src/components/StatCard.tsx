interface Props {
  icon: React.ReactNode;
  label: string;
  value: string | number;
}

export default function StatCard({ icon, label, value }: Props) {
  return (
    <div className="stat-card">
      <div className="stat-label">
        {icon}
        <span>{label}</span>
      </div>
      <div className="stat-value">{value}</div>
    </div>
  );
}
