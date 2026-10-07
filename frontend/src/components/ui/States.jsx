import { AlertCircle, AlertTriangle, CheckCircle2, Info, RotateCw } from 'lucide-react';
import Button from './Button';

const ALERT_ICONS = { info: Info, success: CheckCircle2, warning: AlertTriangle, danger: AlertCircle };

/** Inline callout. `tone`: info | success | warning | danger. */
export function Alert({ tone = 'info', title, children, actions, className = '' }) {
  const Icon = ALERT_ICONS[tone] || Info;
  return (
    <div className={`alert alert-${tone} ${className}`.trim()} role={tone === 'danger' ? 'alert' : 'status'}>
      <Icon size={16} aria-hidden="true" className="alert-icon" />
      <div className="alert-content">
        {title ? <p className="alert-title">{title}</p> : null}
        {children ? <div className="alert-body">{children}</div> : null}
      </div>
      {actions ? <div className="alert-actions">{actions}</div> : null}
    </div>
  );
}

/** Nothing to show yet — explains why and offers the next step. */
export function EmptyState({ icon: Icon, title, description, action, compact = false }) {
  return (
    <div className={`empty-state ${compact ? 'is-compact' : ''}`}>
      {Icon ? (
        <div className="empty-state-icon" aria-hidden="true">
          <Icon size={20} />
        </div>
      ) : null}
      <h3>{title}</h3>
      {description ? <p>{description}</p> : null}
      {action ? <div className="empty-state-action">{action}</div> : null}
    </div>
  );
}

/** A request failed — say what happened and let the user retry when that makes sense. */
export function ErrorState({ title = 'Something went wrong', message, onRetry }) {
  return (
    <div className="error-state" role="alert">
      <AlertCircle size={20} aria-hidden="true" />
      <div>
        <h3>{title}</h3>
        {message ? <p>{message}</p> : null}
      </div>
      {onRetry ? (
        <Button size="sm" icon={RotateCw} onClick={onRetry}>
          Try again
        </Button>
      ) : null}
    </div>
  );
}

export function Skeleton({ width = '100%', height = 14, className = '' }) {
  return <span className={`skeleton ${className}`.trim()} style={{ width, height }} aria-hidden="true" />;
}

/** Placeholder rows shaped like the content that is loading. */
export function LoadingState({ label = 'Loading…', rows = 4, variant = 'rows' }) {
  return (
    <div className={`loading-state loading-${variant}`} role="status" aria-live="polite">
      <span className="visually-hidden">{label}</span>
      {variant === 'metrics' ? (
        <div className="metric-grid">
          {Array.from({ length: rows }, (_, index) => (
            <div key={index} className="metric">
              <Skeleton width="45%" height={12} />
              <Skeleton width="30%" height={24} />
            </div>
          ))}
        </div>
      ) : (
        Array.from({ length: rows }, (_, index) => (
          <div key={index} className="loading-row">
            <Skeleton width="28%" />
            <Skeleton width={`${50 - ((index * 7) % 20)}%`} />
            <Skeleton width="12%" />
          </div>
        ))
      )}
    </div>
  );
}
