import { CircleCheck, CircleDashed, CircleHelp, CircleX } from 'lucide-react';
import Badge from './ui/Badge';

// UNVERIFIED and NO_CANDIDATE are never presented as success: only VERIFIED uses the success tone.
const VERDICTS = {
  VERIFIED: { label: 'Verified', tone: 'success', icon: CircleCheck, hint: 'Functional, security and compatibility checks passed.' },
  UNVERIFIED: { label: 'Unverified', tone: 'warning', icon: CircleHelp, hint: 'Plausible repair; security properties were not tested.' },
  FAILED: { label: 'Failed', tone: 'danger', icon: CircleX, hint: 'A validation or integrity check failed.' },
  NO_CANDIDATE: { label: 'No candidate', tone: 'neutral', icon: CircleDashed, hint: 'The strategy produced no code.' },
};

function VerdictBadge({ verdict, compact = false }) {
  const meta = VERDICTS[verdict] || VERDICTS.NO_CANDIDATE;
  return (
    <Badge tone={meta.tone} icon={meta.icon} title={meta.hint} className={compact ? 'is-compact' : ''}>
      {compact ? <span className="visually-hidden">{meta.label}</span> : meta.label}
    </Badge>
  );
}

export default VerdictBadge;
