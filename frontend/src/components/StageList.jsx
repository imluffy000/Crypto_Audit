import { Check, Clock3, LoaderCircle, MinusCircle, XCircle } from 'lucide-react';

const ICONS = {
  DONE: Check,
  RUNNING: LoaderCircle,
  PENDING: Clock3,
  SKIPPED: MinusCircle,
  FAILED: XCircle,
};

const STATUS_TEXT = { DONE: 'Done', RUNNING: 'In progress', PENDING: 'Waiting', SKIPPED: 'Skipped', FAILED: 'Failed' };

/** Vertical pipeline progress: one row per stage with its status and, while running, a progress bar. */
function StageList({ stages = [] }) {
  return (
    <ol className="stage-list" aria-label="Scan progress">
      {stages.map((stage) => {
        const Icon = ICONS[stage.status] || Clock3;
        const percent = stage.total ? Math.round((stage.current / stage.total) * 100) : null;
        return (
          <li key={stage.stage} className={`stage stage-${stage.status.toLowerCase()}`}>
            <span className="stage-marker" aria-hidden="true">
              <Icon size={13} className={stage.status === 'RUNNING' ? 'spin' : undefined} />
            </span>
            <div className="stage-body">
              <div className="stage-line">
                <span className="stage-label">{stage.label}</span>
                <span className="stage-status">
                  {STATUS_TEXT[stage.status] || stage.status}
                  {stage.status === 'RUNNING' && stage.total ? ` · ${stage.current}/${stage.total}` : ''}
                </span>
              </div>
              {stage.detail ? <p className="stage-detail">{stage.detail}</p> : null}
              {stage.status === 'RUNNING' && percent !== null ? (
                <div className="progress" role="progressbar" aria-label={`${stage.label} progress`} aria-valuemin={0} aria-valuemax={100} aria-valuenow={percent}>
                  <span style={{ width: `${percent}%` }} />
                </div>
              ) : null}
            </div>
          </li>
        );
      })}
    </ol>
  );
}

export default StageList;
