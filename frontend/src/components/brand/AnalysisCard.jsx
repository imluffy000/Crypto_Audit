import { CheckCircle2, TriangleAlert } from 'lucide-react';

const STATUS_ICONS = { success: CheckCircle2, warning: TriangleAlert };

/**
 * A small product-UI fragment: an eyebrow, a title, optional rows, extra content and a status line.
 * `status.tone` is 'success', 'warning' or 'live' (a pulsing dot).
 */
function AnalysisCard({ eyebrow, title, detail, rows, status, children, className = '', style }) {
  const Icon = status ? STATUS_ICONS[status.tone] : null;
  return (
    <div className={`analysis-card ${className}`.trim()} style={style}>
      {eyebrow ? <p className="analysis-card-eyebrow">{eyebrow}</p> : null}
      {title ? <p className="analysis-card-title">{title}</p> : null}
      {detail ? <p className="analysis-card-detail">{detail}</p> : null}
      {rows ? (
        <dl className="analysis-card-rows">
          {rows.map(([value, label]) => (
            <div key={label}>
              <dt>{label}</dt>
              <dd>{value}</dd>
            </div>
          ))}
        </dl>
      ) : null}
      {children}
      {status ? (
        <p className={`analysis-card-status tone-${status.tone}`}>
          {status.caption ? <span className="analysis-card-caption">{status.caption}</span> : null}
          <span className="analysis-card-state">
            {Icon ? <Icon size={14} aria-hidden="true" /> : <span className="live-dot" aria-hidden="true" />}
            {status.label}
          </span>
        </p>
      ) : null}
    </div>
  );
}

export default AnalysisCard;
