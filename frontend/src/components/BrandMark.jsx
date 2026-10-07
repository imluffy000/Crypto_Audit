/** CryptoAudit mark: a plain shield with a check, drawn in the accent colour. */
function BrandMark({ size = 24 }) {
  return (
    <svg className="brand-mark" width={size} height={size} viewBox="0 0 24 24" aria-hidden="true" fill="none">
      <path d="M12 2.5 4.5 5.2v6.1c0 4.6 3.1 8.6 7.5 10.2 4.4-1.6 7.5-5.6 7.5-10.2V5.2L12 2.5Z" fill="currentColor" />
      <path d="m8.6 12.1 2.3 2.3 4.6-4.8" stroke="var(--on-accent)" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export default BrandMark;
