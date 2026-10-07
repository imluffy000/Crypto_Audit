import { useCallback, useEffect, useMemo, useState } from 'react';
import { useParams } from 'react-router-dom';
import DashboardLayout from '../layouts/DashboardLayout';
import CodeCompare from '../components/CodeCompare';
import ExplanationPanel from '../components/ExplanationPanel';
import GateTable from '../components/GateTable';
import VerdictBadge from '../components/VerdictBadge';
import PageHeader, { SectionHeader } from '../components/ui/PageHeader';
import Badge, { SeverityBadge } from '../components/ui/Badge';
import Panel from '../components/ui/Panel';
import Tabs, { TabPanel } from '../components/ui/Tabs';
import { Alert, ErrorState, LoadingState } from '../components/ui/States';
import { scanService } from '../services/scanService';
import { humanize, RULE_NAMES } from '../utils/format';

const TABS_ID = 'strategy';

function ScannerComparison({ baseline, scannerResults }) {
  const tools = Array.from(new Set([...Object.keys(baseline || {}), ...Object.keys(scannerResults || {})])).sort();
  if (!tools.length) return <p className="muted">No external scanners ran for this file.</p>;

  const describe = (flagged) =>
    flagged === null ? <Badge tone="neutral">Unavailable</Badge> : flagged ? <Badge tone="danger">Flags issue</Badge> : <Badge tone="neutral">Clean</Badge>;

  return (
    <>
      <div className="table-scroll bordered">
        <table className="simple-table">
          <thead>
            <tr>
              <th scope="col">Scanner</th>
              <th scope="col">Original</th>
              <th scope="col">Candidate</th>
            </tr>
          </thead>
          <tbody>
            {tools.map((tool) => {
              const before = baseline?.[tool];
              const originalFlagged = before?.available ? (before.relevant_issues || 0) > 0 : null;
              const after = scannerResults?.[tool];
              const candidateFlagged = after === null || after === undefined ? null : !after;
              return (
                <tr key={tool}>
                  <th scope="row" className="mono">
                    {tool}
                  </th>
                  <td>{describe(originalFlagged)}</td>
                  <td>{describe(candidateFlagged)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <p className="muted small">A clean scanner result is evidence, not verification. Only the validation gates decide the verdict.</p>
    </>
  );
}

function FindingSummary({ finding }) {
  const facts = [
    ['Rule', <span key="r"><span className="mono">{finding.rule_id}</span> · {RULE_NAMES[finding.rule_id] || humanize(finding.category)}</span>],
    ['Severity', <SeverityBadge key="s" severity={finding.severity} />],
    ['Confidence', humanize(finding.confidence)],
    ['Matched API', <span key="m" className="mono">{finding.matched_api}</span>],
  ];
  return (
    <div className="finding-summary">
      <dl className="definition-grid">
        {facts.map(([term, value]) => (
          <div key={term}>
            <dt>{term}</dt>
            <dd>{value}</dd>
          </div>
        ))}
      </dl>
      <div className="finding-text">
        <p>{finding.explanation}</p>
        <pre className="evidence mono" aria-label="Evidence">
          {finding.evidence}
        </pre>
        <p className="muted">
          <strong className="text-strong">Guidance.</strong> {finding.remediation}
        </p>
      </div>
    </div>
  );
}

function FindingDetail() {
  const { scanId, findingId } = useParams();
  const [detail, setDetail] = useState(null);
  const [active, setActive] = useState(null);
  const [error, setError] = useState('');

  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let current = true;
    scanService
      .getFinding(scanId, findingId)
      .then((data) => {
        if (!current) return;
        setDetail(data);
        const preferred = data.runs.find((run) => run.targets_finding && run.verdict !== 'NO_CANDIDATE') || data.runs[0];
        setActive(preferred?.strategy_id || null);
      })
      .catch((err) => current && setError(err.message));
    return () => {
      current = false;
    };
  }, [scanId, findingId, reloadKey]);

  const reload = useCallback(() => {
    setError('');
    setDetail(null);
    setReloadKey((key) => key + 1);
  }, []);

  const markers = useMemo(() => {
    const result = {};
    (detail?.file_findings || []).forEach((f) => {
      result[f.line] = [...(result[f.line] || []).filter((m) => m.label !== f.rule_id), { label: f.rule_id, tone: 'warning' }];
    });
    return result;
  }, [detail]);

  const crumbs = [
    { label: 'Scans', to: '/reports' },
    { label: detail?.repository || 'Scan', to: `/scans/${scanId}` },
    { label: 'Finding' },
  ];

  if (error || !detail) {
    return (
      <DashboardLayout>
        <PageHeader breadcrumbs={crumbs} title="Finding" />
        {error ? <ErrorState title="Could not load this finding" message={error} onRetry={reload} /> : <LoadingState rows={6} label="Loading finding" />}
      </DashboardLayout>
    );
  }

  const { finding } = detail;
  const run = detail.runs.find((r) => r.strategy_id === active);
  const findingLines = detail.file_findings.map((f) => f.line);

  return (
    <DashboardLayout width="wide">
      <PageHeader
        breadcrumbs={crumbs}
        title={
          <>
            {detail.file_path}
            <span className="muted">:{finding.line}</span>
          </>
        }
        mono
        meta={
          <>
            <span>
              Best result <VerdictBadge verdict={detail.best_verdict} />
            </span>
            <span className="mono">{detail.repository}</span>
          </>
        }
      />

      <Panel title="What CryptoAudit found">
        <FindingSummary finding={finding} />
      </Panel>

      <section aria-labelledby="candidates-heading" className="stack">
        <SectionHeader id="candidates-heading" title="Repair candidates" description="Each strategy proposes a candidate for the whole file; validation runs on each independently." />
        {detail.runs.length ? (
          <>
            <Tabs
              idBase={TABS_ID}
              label="Repair strategy"
              value={active}
              onChange={setActive}
              tabs={detail.runs.map((r) => ({ id: r.strategy_id, label: r.strategy_id, adornment: <VerdictBadge verdict={r.verdict} compact /> }))}
            />
            {run ? (
              <TabPanel idBase={TABS_ID} id={run.strategy_id} className="tab-panel stack">
                <div className="candidate-head">
                  <VerdictBadge verdict={run.verdict} />
                  <span className="muted">{run.explanation.headline}</span>
                </div>
                {!run.targets_finding && run.candidate_code ? (
                  <Alert tone="info">This candidate repairs other findings in the file but leaves this one unchanged.</Alert>
                ) : null}
                {run.failure_reason ? (
                  <Alert tone="warning" title={`No usable candidate (${humanize(run.repair_status)})`}>
                    {run.failure_reason}
                  </Alert>
                ) : null}

                <CodeCompare
                  original={detail.original_source}
                  repaired={run.candidate_code}
                  diff={run.diff}
                  path={detail.file_path}
                  findingLines={findingLines}
                  findingMarkers={markers}
                />

                <div className="detail-grid">
                  <Panel title="Why this verdict" headingLevel={3}>
                    <ExplanationPanel key={run.candidate_id} scanId={scanId} run={run} aiAvailable={detail.ai_available} />
                  </Panel>
                  <div className="stack">
                    <Panel title="Validation gates" headingLevel={3}>
                      <GateTable gates={run.gates} />
                    </Panel>
                    <Panel title="Scanners vs validation" headingLevel={3}>
                      <ScannerComparison baseline={detail.baseline} scannerResults={run.scanner_results} />
                    </Panel>
                  </div>
                </div>
              </TabPanel>
            ) : null}
          </>
        ) : (
          <Alert tone="warning" title="No repair strategies ran for this file" />
        )}
      </section>
    </DashboardLayout>
  );
}

export default FindingDetail;
