interface Props {
  title: string;
  icon: React.ReactNode;
  content: string;
}

export default function InsightSectionCard({ title, icon, content }: Props) {
  return (
    <div className="card section-card">
      <div className="card-title with-icon">
        {icon}
        <span>{title}</span>
      </div>

      <p className="card-text">{content || "暂无分析内容"}</p>
    </div>
  );
}
