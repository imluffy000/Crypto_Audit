import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft, Scale, ShieldAlert } from 'lucide-react';
import DashboardLayout from '../layouts/DashboardLayout';
import CodeCompare from '../components/CodeCompare';
import ExplanationPanel from '../components/ExplanationPanel';
import GateTable from '../components/GateTable';
import VerdictBadge from '../components/VerdictBadge';
import { scanService } from '../services/scanService';

function ScannerComparison({ baseline, scannerResults }) {
  const tools = Array.from(new Set([...Object.keys(baseline || {}), ...Object.keys(scannerResults || {})])).sort();
  const describe = (value) => (value === null || value === undefined ? 'unavailable' : value ? 'clean' : 'flags issue');
  return (
    <div className="scanner-table">
      <div className="scanner-row header">
        <span>Tool</span>
        <span>Original code</span>
        <span>Repaired candidate</span>
      </div>
      {tools.map((tool) => {
        const before = baseline?.[tool];
        const originalFlagged = before?.available ? (before.relevant_issues || 0) > 0 : null;
        return (
          <div key={tool} className="scanner-row">
            <span>{tool}</span>
            <span>{originalFlagged === null ? 'unavailable' : originalFlagged ? 'flags issue' : 'clean'}</span>
            <span>{describe(scannerResults?.[tool])}</span>
          </div>
        );
      })}
    </div>
  );
}

function FindingDetail() {
  const { scanId, findingId } = useParams();
  const navigate = useNavigate();
  const [detail, setDetail] = useState(null);
  const [active, setActive] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    scanService
      .getFinding(scanId, findingId)
      .then((data) => {
        setDetail(data);
        const preferred = data.runs.find((run) => run.targets_finding && run.verdict !== 'NO_CANDIDATE') || data.runs[0];
        setActive(preferred?.strategy_id || null);
      })
      .catch((err) => setError(err.message));
  }, [scanId, findingId]);

  if (error) {
    return (
      <DashboardLayout>
        <div className="form-error">{error}</div>
      </DashboardLayout>
    );
  }
  if (!detail) {
    return (
      <DashboardLayout>
        <p className="subtitle">Loading finding…</p>
      </DashboardLayout>
    );
  }

  const { finding } = detail;
  const run = detail.runs.find((r) => r.strategy_id === active);
  const findingLines = detail.file_findings.map((f) => f.line);

  return (
    <DashboardLayout>
      <div className="page-header">
        <div>
          <p className="eyebrow">
            {finding.rule_id} · {finding.category.replaceAll('_', ' ').toLowerCase()} · {finding.severity}
          </p>
          <h1>
            <code>{detail.file_path}</code>:{finding.line}
          </h1>
          <p className="subtitle">{detail.repository}</p>
        </div>
        <div className="header-actions small-gap">
          <VerdictBadge verdict={detail.best_verdict} />
          <button type="button" className="secondary-button" onClick={() => navigate(`/scans/${scanId}`)}>
            <ArrowLeft size={14} /> Back to scan
          </button>
        </div>
      </div>

      <div className="card-panel">
        <h2>
          <ShieldAlert size={17} /> What CryptoAudit found
        </h2>
        <p>{finding.explanation}</p>
        <pre className="evidence">{finding.evidence}</pre>
        <p className="subtitle">
          <strong>Guidance:</strong> {finding.remediation}
        </p>
      </div>

      <div className="tab-row strategy-tabs">
        {detail.runs.map((r) => (
          <button
            key={r.strategy_id}
            type="button"
            className={`tab-button ${active === r.strategy_id ? 'active' : ''}`}
            onClick={() => setActive(r.strategy_id)}
          >
            {r.strategy_id} <VerdictBadge verdict={r.verdict} compact />
          </button>
        ))}
      </div>

      {run ? (
        <>
          <div className="card-panel">
            <div className="panel-header-row">
              <h2>Original vs repaired ({run.strategy_id})</h2>
              <VerdictBadge verdict={run.verdict} />
            </div>
            {!run.targets_finding && run.candidate_code ? (
              <p className="subtitle">This candidate repairs other findings in the file but leaves this one unchanged.</p>
            ) : null}
            <CodeCompare original={detail.original_source} repaired={run.candidate_code} diff={run.diff} findingLines={findingLines} />
          </div>

          <div className="detail-grid">
            <div className="card-panel">
              <h2>Why — {run.explanation.headline.split(':')[0]}</h2>
              <ExplanationPanel key={run.candidate_id} scanId={scanId} run={run} aiAvailable={detail.ai_available} />
            </div>
            <div>
              <div className="card-panel">
                <h2>Validation gates</h2>
                <GateTable gates={run.gates} />
              </div>
              <div className="card-panel">
                <h2>
                  <Scale size={17} /> Scanners vs validation
                </h2>
                <ScannerComparison baseline={detail.baseline} scannerResults={run.scanner_results} />
              </div>
            </div>
          </div>
        </>
      ) : null}
    </DashboardLayout>
  );
}

export default FindingDetail;
