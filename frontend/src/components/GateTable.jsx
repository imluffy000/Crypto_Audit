import Badge from './ui/Badge';
import { humanize } from '../utils/format';

const GATE_NAMES = {
  V0: 'Scanner re-scan',
  V1: 'Functional',
  V2: 'Security properties',
  V3: 'Legacy compatibility',
};

// Only PASS reads as success; NOT_APPLICABLE is neutral and NOT_RUN is a warning, never a pass.
const STATUS_TONE = { PASS: 'success', FAIL: 'danger', ERROR: 'danger', NOT_APPLICABLE: 'neutral', NOT_RUN: 'warning' };

function GateTable({ gates = [] }) {
  if (!gates.length) return <p className="muted">No validation gates ran for this candidate.</p>;
  return (
    <ol className="gate-list">
      {gates.map((gate) => {
        const failing = (gate.checks || []).filter((check) => check.status !== 'PASS');
        return (
          <li key={gate.gate} className="gate-item">
            <div className="gate-head">
              <span className="gate-id mono">{gate.gate}</span>
              <span className="gate-name">{GATE_NAMES[gate.gate] || gate.gate}</span>
              <span className="gate-role">{gate.gate === 'V0' ? 'Evidence only' : gate.gating ? 'Gating' : 'Non-gating'}</span>
              <Badge tone={STATUS_TONE[gate.status] || 'warning'}>{humanize(gate.status)}</Badge>
            </div>
            {gate.summary ? <p className="gate-summary">{gate.summary}</p> : null}
            {failing.length ? (
              <ul className="gate-checks">
                {failing.map((check) => (
                  <li key={check.name}>
                    <code>{check.name}</code>
                    <span>{check.message || humanize(check.status)}</span>
                  </li>
                ))}
              </ul>
            ) : null}
          </li>
        );
      })}
    </ol>
  );
}

export default GateTable;
