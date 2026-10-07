import { SEVERITY_ORDER } from '../../utils/format';

/** Small label. `tone`: neutral | accent | success | warning | danger | info. */
function Badge({ tone = 'neutral', icon: Icon, children, title, className = '', mono = false }) {
  return (
    <span className={`badge badge-${tone} ${mono ? 'mono' : ''} ${className}`.trim()} title={title}>
      {Icon ? <Icon size={12} aria-hidden="true" /> : null}
      {children}
    </span>
  );
}

const SEVERITY_TONE = { CRITICAL: 'danger', HIGH: 'danger', MEDIUM: 'warning', LOW: 'info' };

/** Severity with a four-step bar so it reads without relying on colour alone. */
export function SeverityBadge({ severity }) {
  const tone = SEVERITY_TONE[severity] || 'neutral';
  const level = SEVERITY_ORDER[severity] || 0;
  return (
    <span className={`severity tone-${tone}`}>
      <span className="severity-bars" aria-hidden="true">
        {[1, 2, 3, 4].map((step) => (
          <span key={step} className={step <= level ? 'on' : ''} />
        ))}
      </span>
      {severity ? severity.charAt(0) + severity.slice(1).toLowerCase() : 'Unknown'}
    </span>
  );
}

export default Badge;
