import { Check, Clock3, LoaderCircle, MinusCircle, XCircle } from 'lucide-react';

const ICONS = {
  DONE: Check,
  RUNNING: LoaderCircle,
  PENDING: Clock3,
  SKIPPED: MinusCircle,
  FAILED: XCircle,
};

function StageList({ stages = [] }) {
  return (
    <ul className="step-list stage-list">
      {stages.map((stage) => {
        const Icon = ICONS[stage.status] || Clock3;
        const counter = stage.total ? ` (${stage.current}/${stage.total})` : '';
        return (
          <li key={stage.stage} className={`stage-${stage.status.toLowerCase()}`}>
            <span className="step-marker">
              <Icon size={12} className={stage.status === 'RUNNING' ? 'spin' : undefined} />
            </span>
            <span>
              <strong>{stage.label}</strong>
              {stage.detail ? <small>{` — ${stage.detail}${stage.status === 'RUNNING' ? counter : ''}`}</small> : null}
            </span>
          </li>
        );
      })}
    </ul>
  );
}

export default StageList;
