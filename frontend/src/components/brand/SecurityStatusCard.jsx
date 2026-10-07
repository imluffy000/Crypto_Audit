import { CheckCircle2, TriangleAlert } from 'lucide-react';

const STATUS_ICONS = { success: CheckCircle2, warning: TriangleAlert };

/**
 * A small product-UI fragment: an eyebrow, a title, optional rows and a status line.
 * `status.tone` is 'success', 'warning' or 'live' (a pulsing dot for work in progress or just finished).
 */
function SecurityStatusCard({ eyebrow, title, detail, rows, status, className = '', style }) {
  const Icon = status ? STATUS_ICONS[status.tone] : null;
  return (
    <div className={`status-card ${className}`.trim()} style={style}>
      {eyebrow ? <p className="status-card-eyebrow">{eyebrow}</p> : null}
      {title ? <p className="status-card-title">{title}</p> : null}
      {detail ? <p className="status-card-detail">{detail}</p> : null}
      {rows ? (
        <dl className="status-card-rows">
          {rows.map(([value, label]) => (
            <div key={label}>
              <dt>{label}</dt>
              <dd>{value}</dd>
            </div>
          ))}
        </dl>
      ) : null}
      {status ? (
        <p className={`status-card-status tone-${status.tone}`}>
          {status.caption ? <span className="status-card-caption">{status.caption}</span> : null}
          <span className="status-card-state">
            {Icon ? <Icon size={14} aria-hidden="true" /> : <span className="status-dot" aria-hidden="true" />}
            {status.label}
          </span>
        </p>
      ) : null}
    </div>
  );
}

export default SecurityStatusCard;
