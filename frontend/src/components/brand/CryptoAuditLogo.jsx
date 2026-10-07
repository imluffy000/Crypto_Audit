/** CryptoAudit identity: a shield with a keyhole on a rounded tile, plus the wordmark. */
function CryptoAuditLogo({ size = 32, wordmark = true, className = '' }) {
  return (
    <span className={`ca-logo ${className}`.trim()}>
      <svg className="ca-logo-mark" width={size} height={size} viewBox="0 0 32 32" aria-hidden="true" fill="none">
        <rect width="32" height="32" rx="9" fill="currentColor" />
        <path d="M16 6.5 9 9.1v5.5c0 4.3 2.9 8 7 9.4 4.1-1.4 7-5.1 7-9.4V9.1L16 6.5Z" stroke="#ffffff" strokeWidth="1.8" strokeLinejoin="round" />
        <circle cx="16" cy="13.9" r="2" fill="#D9F99D" />
        <rect x="15.1" y="15.2" width="1.8" height="3.8" rx="0.9" fill="#D9F99D" />
      </svg>
      {wordmark ? <span className="ca-logo-word">CryptoAudit</span> : null}
    </span>
  );
}

export default CryptoAuditLogo;
