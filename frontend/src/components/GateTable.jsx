const GATE_NAMES = {
  V0: 'Scanner re-scan',
  V1: 'Functional',
  V2: 'Security properties',
  V3: 'Legacy compatibility',
};

function GateTable({ gates = [] }) {
  return (
    <div className="gate-table">
      {gates.map((gate) => {
        const failing = (gate.checks || []).filter((check) => check.status !== 'PASS');
        return (
          <div key={gate.gate} className="gate-row">
            <div className="gate-id">
              <strong>{gate.gate}</strong>
              <small>{GATE_NAMES[gate.gate]}</small>
            </div>
            <span className={`gate-status ${gate.status.toLowerCase()}`}>{gate.status.replace('_', ' ')}</span>
            <span className="gate-role">{gate.gate === 'V0' ? 'evidence only' : gate.gating ? 'gating' : 'non-gating'}</span>
            <div className="gate-summary">
              {gate.summary}
              {failing.length ? (
                <ul>
                  {failing.map((check) => (
                    <li key={check.name}>
                      <code>{check.name}</code>: {check.message || check.status}
                    </li>
                  ))}
                </ul>
              ) : null}
            </div>
          </div>
        );
      })}
    </div>
  );
}

export default GateTable;
