import { useId } from 'react';
import { CheckCircle2 } from 'lucide-react';

// A tall, hand-like organic outline: asymmetric, with a few soft irregular curves.
const SILHOUETTE =
  'M246 36C318 26 384 58 410 122c14 34 44 50 74 82 40 44 46 104 26 158-14 38-6 74-8 112-4 70-58 108-128 116-62 8-118 2-174-12C38 562 18 500 40 438c14-40 4-78-6-118-18-74 8-138 56-186 34-34 56-62 82-78 22-12 46-18 74-20Z';

/**
 * Sign-in artwork: one organic teal silhouette with oversized circles and rounded rectangles layered
 * inside and slightly beyond it, a few faint cryptographic details (shield, key, hash, scan arc), and a
 * single floating status pill. Decorative only.
 */
function LoginArtwork({ className = '' }) {
  const clip = `login-art-${useId().replace(/:/g, '')}`;

  return (
    <div className={`login-art ${className}`.trim()} aria-hidden="true">
      <div className="login-art-frame">
        <svg className="login-art-svg" viewBox="0 0 560 640" focusable="false">
          <defs>
            <clipPath id={clip}>
              <path d={SILHOUETTE} />
            </clipPath>
          </defs>

          {/* Main silhouette */}
          <path className="login-art-silhouette" d={SILHOUETTE} fill="#0F766E" />

          {/* Shapes clipped to the silhouette: tonal layers */}
          <g clipPath={`url(#${clip})`}>
            <rect x="372" y="64" width="230" height="214" rx="76" fill="#0B5D56" />
            <rect x="96" y="400" width="320" height="150" rx="64" fill="#115E59" />
            <rect x="20" y="300" width="150" height="130" rx="52" fill="#14B8A6" opacity="0.22" />
          </g>

          {/* Large circle, upper middle, spilling past the edge */}
          <circle cx="296" cy="214" r="126" fill="#14B8A6" />
          <circle className="login-art-drift" cx="214" cy="292" r="86" fill="#14B8A6" opacity="0.45" />

          {/* Scan arc around the large circle */}
          <g className="login-art-scan">
            <circle cx="296" cy="214" r="146" fill="none" stroke="#FFFFFF" strokeOpacity="0.55" strokeWidth="2.5" strokeLinecap="round" strokeDasharray="70 848" />
          </g>

          {/* Stacked rounded rectangles: centre and bottom */}
          <rect x="250" y="300" width="250" height="168" rx="64" fill="#D9F99D" />
          <rect x="162" y="352" width="210" height="156" rx="60" fill="#14B8A6" opacity="0.62" />
          <rect x="56" y="520" width="360" height="68" rx="34" fill="#14B8A6" opacity="0.38" />

          {/* White circle with a small shield */}
          <circle cx="178" cy="452" r="44" fill="#FFFFFF" />
          <path d="M178 434l-13 5v9.5c0 8 5.6 14.8 13 17.5 7.4-2.7 13-9.5 13-17.5V439l-13-5Z" fill="none" stroke="#0F766E" strokeWidth="2.4" strokeLinejoin="round" />
          <path d="m172.5 450.5 4 4 7.5-8" fill="none" stroke="#0F766E" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" />

          {/* Faint details: a key on the lime slab, a hash mark on the silhouette */}
          <g stroke="#0F766E" strokeOpacity="0.45" strokeWidth="3" strokeLinecap="round" fill="none">
            <circle cx="430" cy="352" r="11" />
            <path d="M419 352h-30m10 0v9m-8-9v6" />
          </g>
          <g stroke="#FFFFFF" strokeOpacity="0.28" strokeWidth="3" strokeLinecap="round">
            <path d="M118 196l-6 34m22-34-6 34m-22-23h30m-32 12h30" />
          </g>
        </svg>

        <span className="login-art-pill">
          <CheckCircle2 size={16} aria-hidden="true" />
          Analysis complete
        </span>
      </div>
    </div>
  );
}

export default LoginArtwork;
