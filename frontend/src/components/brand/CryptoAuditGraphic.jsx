import { useId } from 'react';

// Ciphertext-like rows engraved on the dark slab. Purely decorative.
const HEX_ROWS = [
  '3f a9 0c 7e d2 44 b1 58',
  'e7 15 9b c4 02 6d f8 31',
  '8a 5e 27 f0 bc 93 4d 16',
  'c1 7b e4 39 a6 0f 82 d5',
  '54 d8 1a 6f 3c e9 b7 20',
  '9d 26 f3 81 47 ca 0b 6e',
  'b4 0e 5a d1 78 2f c6 93',
];

/**
 * CryptoAudit's abstract identity artwork: an organic blob, a dark "ciphertext" slab, a lime circle
 * with a rotating scan ring and a few secondary shapes. Product-UI fragments (AnalysisCard,
 * AlgorithmBadge) are passed as children and positioned by the caller. Decorative only: hidden
 * from assistive technology. `compact` drops the secondary shapes for small spaces.
 */
function CryptoAuditGraphic({ compact = false, className = '', children }) {
  const id = useId().replace(/:/g, '');
  const slabClip = `slab-${id}`;
  const dots = `dots-${id}`;

  return (
    <div className={`crypto-graphic ${compact ? 'is-compact' : ''} ${className}`.trim()} aria-hidden="true">
      <svg className="crypto-graphic-art" viewBox="0 0 560 620" preserveAspectRatio="xMidYMid slice" focusable="false">
        <defs>
          <clipPath id={slabClip}>
            <rect x="250" y="262" width="380" height="350" rx="48" transform="rotate(-10 440 437)" />
          </clipPath>
          <pattern id={dots} width="16" height="16" patternUnits="userSpaceOnUse">
            <circle cx="2" cy="2" r="1.6" fill="#0F766E" opacity="0.28" />
          </pattern>
        </defs>

        {/* 1. Organic background blob */}
        <path
          className="art-blob"
          d="M318 42c86 6 170 52 204 136 34 83 9 166-30 242-40 77-104 152-190 160-86 9-170-48-221-121C30 386 8 296 38 216 68 135 124 70 196 50c40-11 81-11 122-8Z"
          fill="#14B8A6"
          opacity="0.14"
        />
        <rect className="art-secondary" x="388" y="46" width="144" height="112" fill={`url(#${dots})`} />

        {/* 2. Dark slab, bleeding off the right and bottom edges */}
        <rect x="250" y="262" width="380" height="350" rx="48" transform="rotate(-10 440 437)" fill="#0F766E" />
        <g clipPath={`url(#${slabClip})`} transform="rotate(-10 440 437)">
          {HEX_ROWS.map((row, index) => (
            <text key={row} x="300" y={340 + index * 34} className="art-hex">
              {row}
            </text>
          ))}
        </g>

        {/* 3. Lime circle and scan rings */}
        <circle cx="214" cy="262" r="124" fill="#D9F99D" opacity="0.92" />
        <circle cx="214" cy="262" r="160" fill="none" stroke="#0F766E" strokeOpacity="0.2" strokeWidth="1.5" />
        <circle className="art-secondary" cx="214" cy="262" r="196" fill="none" stroke="#0F766E" strokeOpacity="0.12" strokeWidth="1.5" strokeDasharray="2 8" />
        <g className="art-scan">
          <circle cx="214" cy="262" r="160" fill="none" stroke="#0F766E" strokeWidth="3" strokeLinecap="round" strokeDasharray="90 916" />
        </g>

        {/* 4. Secondary shapes */}
        <rect className="art-secondary" x="44" y="452" width="200" height="128" rx="34" fill="#FEF7E5" stroke="#D9E2DC" />
        <g className="art-orbit">
          <circle className="art-secondary" cx="482" cy="206" r="30" fill="none" stroke="#0F766E" strokeWidth="2" />
          <circle cx="482" cy="206" r="9" fill="#14B8A6" />
        </g>
      </svg>
      {children}
    </div>
  );
}

export default CryptoAuditGraphic;
