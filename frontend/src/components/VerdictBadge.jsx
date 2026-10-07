import { CircleCheck, CircleDashed, CircleHelp, CircleX } from 'lucide-react';

const VERDICTS = {
  VERIFIED: { label: 'Verified', className: 'verified', icon: CircleCheck, hint: 'Functional, security and compatibility checks passed.' },
  UNVERIFIED: { label: 'Unverified', className: 'unverified', icon: CircleHelp, hint: 'Plausible repair; security properties were not tested.' },
  FAILED: { label: 'Failed', className: 'failed', icon: CircleX, hint: 'A validation or integrity check failed.' },
  NO_CANDIDATE: { label: 'No candidate', className: 'none', icon: CircleDashed, hint: 'The strategy produced no code.' },
};

function VerdictBadge({ verdict, compact = false }) {
  const meta = VERDICTS[verdict] || VERDICTS.NO_CANDIDATE;
  const Icon = meta.icon;
  return (
    <span className={`verdict-badge ${meta.className}`} title={meta.hint}>
      <Icon size={13} /> {compact ? null : meta.label}
    </span>
  );
}

export default VerdictBadge;
