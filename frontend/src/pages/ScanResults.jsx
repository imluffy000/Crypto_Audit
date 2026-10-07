import { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { AlertTriangle, ArrowLeft, Download, FileWarning, ShieldAlert } from 'lucide-react';
import DashboardLayout from '../layouts/DashboardLayout';
import StageList from '../components/StageList';
import VerdictBadge from '../components/VerdictBadge';
import { scanService } from '../services/scanService';

const POLL_MS = 1500;
const FINISHED = ['COMPLETED', 'FAILED'];

function ScanResults() {
  const { scanId } = useParams();
  const navigate = useNavigate();
  const [scan, setScan] = useState(null);
  const [findings, setFindings] = useState([]);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;
    let timer;
    const poll = async () => {
      try {
        const next = await scanService.getScan(scanId);
        if (cancelled) return;
        setScan(next);
        if (next.status === 'COMPLETED') {
          const list = await scanService.getFindings(scanId);
          if (!cancelled) setFindings(list);
        } else if (!FINISHED.includes(next.status)) {
          timer = setTimeout(poll, POLL_MS);
        }
      } catch (err) {
        if (!cancelled) setError(err.message);
      }
    };
    poll();
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [scanId]);

  const strategies = scan?.strategies || [];
  const summary = scan?.summary;

  return (
    <DashboardLayout>
      <div className="page-header">
        <div>
          <p className="eyebrow">Security scan {scan ? `· ${scan.status.toLowerCase()}` : ''}</p>
          <h1>{scan?.repository || 'Loading scan…'}</h1>
          {scan ? (
            <p className="subtitle">
              Branch <code>{scan.ref}</code>
              {scan.commit ? <> · commit <code>{scan.commit}</code></> : null} · started {new Date(scan.created_at).toLocaleString()}
            </p>
          ) : null}
        </div>
        <div className="header-actions small-gap">
          <button type="button" className="secondary-button" onClick={() => navigate('/reports')}>
            <ArrowLeft size={14} /> All scans
          </button>
          {scan?.status === 'COMPLETED' ? (
            <a className="primary-button" href={scanService.reportUrl(scanId)}>
              <Download size={15} /> Download report
            </a>
          ) : null}
        </div>
      </div>

      {error ? <div className="form-error">{error}</div> : null}

      {scan && scan.status !== 'COMPLETED' ? (
        <div className="card-panel stage-panel">
          <StageList stages={scan.stages} />
          {scan.status === 'FAILED' ? (
            <div className="alert-box danger">
              <ShieldAlert size={15} />
              <div>
                <strong>Scan failed ({scan.error?.code}).</strong>
                <p>{scan.error?.message}</p>
              </div>
            </div>
          ) : null}
        </div>
      ) : null}

      {summary ? (
        <>
          <div className="stats-grid">
            <div className="stat-card">
              <span>Python files</span>
              <strong>{summary.files_scanned}</strong>
              <small>{scan.skipped_files.length} skipped</small>
            </div>
            <div className="stat-card">
              <span>Findings</span>
              <strong>{summary.findings}</strong>
              <small>{Object.entries(summary.findings_by_rule).map(([rule, n]) => `${rule}: ${n}`).join(' · ') || 'none'}</small>
            </div>
            <div className="stat-card">
              <span>Files affected</span>
              <strong>{summary.files_with_findings}</strong>
              <small>Strategies: {strategies.join(', ')}</small>
            </div>
            <div className="stat-card">
              <span>Scanner-clean, not verified</span>
              <strong>{summary.scanner_clean_not_verified}</strong>
              <small>Scanner silence is not proof</small>
            </div>
          </div>

          {Object.entries(scan.skipped_strategies).map(([strategy, reason]) => (
            <div key={strategy} className="alert-box warning">
              <AlertTriangle size={15} />
              <div>
                <p>
                  <strong>{strategy} skipped:</strong> {reason}
                </p>
              </div>
            </div>
          ))}

          <div className="card-panel">
            <div className="panel-header-row">
              <h2>
                <FileWarning size={17} /> Findings
              </h2>
            </div>
            {findings.length ? (
              <div className="findings-table">
                <div className="findings-row header">
                  <span>Location</span>
                  <span>Rule</span>
                  <span>Issue</span>
                  <span>Best result</span>
                  {strategies.map((s) => (
                    <span key={s}>{s}</span>
                  ))}
                </div>
                {findings.map((item) => (
                  <Link key={item.finding_id} className="findings-row" to={`/scans/${scanId}/findings/${item.finding_id}`}>
                    <span>
                      <code>{item.finding.file}</code>:{item.finding.line}
                    </span>
                    <span className="rule-tag">{item.finding.rule_id}</span>
                    <span className="finding-text">{item.finding.explanation}</span>
                    <span>
                      <VerdictBadge verdict={item.best_verdict} />
                    </span>
                    {strategies.map((s) => (
                      <span key={s}>{item.verdicts[s] ? <VerdictBadge verdict={item.verdicts[s]} compact /> : '–'}</span>
                    ))}
                  </Link>
                ))}
              </div>
            ) : (
              <div className="empty-state compact">
                <h3>No cryptographic misuse found.</h3>
                <p>CryptoAudit's CR1–CR5 rules did not flag any of the scanned Python files.</p>
              </div>
            )}
          </div>

          {scan.skipped_files.length ? (
            <div className="card-panel">
              <h2>Skipped files</h2>
              <ul className="plain-list">
                {scan.skipped_files.map((file) => (
                  <li key={file.path}>
                    <code>{file.path}</code> — {file.reason}
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
        </>
      ) : null}
    </DashboardLayout>
  );
}

export default ScanResults;
