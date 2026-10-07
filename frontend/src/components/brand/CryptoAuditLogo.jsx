import { useId } from 'react';

// The symbol: a geometric shield whose counter is an open "C" (CryptoAudit, and code) with a single
// lime point at its centre, the audited bit. Drawn on a 32-unit grid; holds up at 16px.
const SHIELD = 'M16 2.6 27 6.4v8.4c0 6.9-4.5 12.3-11 14.6C9.5 27.1 5 21.7 5 14.8V6.4L16 2.6Z';
const C_ARC = 'M19.9 11.1A6 6 0 1 0 19.9 20.1';
const STROKE = 3.2;

/**
 * The CryptoAudit symbol in one of three variants:
 *   color — teal shield, white "C", lime point (default; light or dark backgrounds)
 *   dark  — a single near-black shape with the "C" and point cut out (light backgrounds)
 *   white — the same in white (dark backgrounds)
 */
export function CryptoAuditMark({ size = 32, variant = 'color', className = '' }) {
  const mask = `ca-mark-${useId().replace(/:/g, '')}`;

  if (variant === 'color') {
    return (
      <svg className={`ca-logo-mark ${className}`.trim()} width={size} height={size} viewBox="0 0 32 32" aria-hidden="true" focusable="false">
        <path d={SHIELD} fill="#0F766E" />
        <path d={C_ARC} fill="none" stroke="#FFFFFF" strokeWidth={STROKE} strokeLinecap="round" />
        <circle cx="16" cy="15.6" r="1.9" fill="#D9F99D" />
      </svg>
    );
  }

  return (
    <svg className={`ca-logo-mark ${className}`.trim()} width={size} height={size} viewBox="0 0 32 32" aria-hidden="true" focusable="false">
      <defs>
        <mask id={mask} maskUnits="userSpaceOnUse" x="0" y="0" width="32" height="32">
          <path d={SHIELD} fill="#FFFFFF" />
          <path d={C_ARC} fill="none" stroke="#000000" strokeWidth={STROKE} strokeLinecap="round" />
          <circle cx="16" cy="15.6" r="1.9" fill="#000000" />
        </mask>
      </defs>
      <rect width="32" height="32" fill={variant === 'white' ? '#FFFFFF' : '#17201D'} mask={`url(#${mask})`} />
    </svg>
  );
}

/** Symbol plus the "CryptoAudit" wordmark (semibold). `wordmark={false}` gives the symbol alone. */
function CryptoAuditLogo({ size = 32, variant = 'color', wordmark = true, className = '' }) {
  return (
    <span className={`ca-logo ca-logo-${variant} ${className}`.trim()}>
      <CryptoAuditMark size={size} variant={variant} />
      {wordmark ? <span className="ca-logo-word">CryptoAudit</span> : null}
    </span>
  );
}

export default CryptoAuditLogo;
