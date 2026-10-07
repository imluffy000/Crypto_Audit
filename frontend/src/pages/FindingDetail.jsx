import { Fragment, useCallback, useEffect, useMemo, useState } from 'react';
import { useParams } from 'react-router-dom';
import { ArrowLeft, ChevronLeft, ChevronRight, Copy, ExternalLink, Lightbulb } from 'lucide-react';
import DashboardLayout from '../layouts/DashboardLayout';
import CodeCompare from '../components/CodeCompare';
import ExplanationPanel from '../components/ExplanationPanel';
import GateTable from '../components/GateTable';
import VerdictBadge from '../components/VerdictBadge';
import Button from '../components/ui/Button';
import PageHeader, { SectionHeader } from '../components/ui/PageHeader';
import Badge, { SeverityBadge } from '../components/ui/Badge';
import Panel from '../components/ui/Panel';
import Tabs, { TabPanel } from '../components/ui/Tabs';
import { Alert, ErrorState, LoadingState } from '../components/ui/States';
import { useToast } from '../components/ui/toastContext';
import { scanService } from '../services/scanService';
import { humanize, RULE_NAMES, SEVERITY_ORDER } from '../utils/format';

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

// Lets long dotted API names wrap at a dot instead of in the middle of a word.
function breakAtDots(text) {
  return String(text || '')
    .split('.')
    .map((part, index, parts) => (
      <Fragment key={index}>
        {part}
        {index < parts.length - 1 ? (
          <>
            .<wbr />
          </>
        ) : null}
      </Fragment>
    ));
}

function FindingSummary({ finding }) {
  return (
    <div className="finding-summary">
      <div className="finding-facts">
        <SeverityBadge severity={finding.severity} />
        <Badge tone="neutral">
          <span className="mono">{finding.rule_id}</span> · {RULE_NAMES[finding.rule_id] || humanize(finding.category)}
        </Badge>
        <Badge tone="neutral">Confidence: {humanize(finding.confidence)}</Badge>
      </div>

      <p className="finding-lead">{finding.explanation}</p>

      <figure className="evidence-block">
        <figcaption>Line {finding.line}</figcaption>
        <pre className="evidence mono" aria-label="Evidence">
          {finding.evidence}
        </pre>
      </figure>

      <dl className="finding-api">
        <dt>Matched API</dt>
        <dd className="mono">{breakAtDots(finding.matched_api)}</dd>
      </dl>

      <div className="guidance">
        <Lightbulb size={18} aria-hidden="true" />
        <div>
          <p className="guidance-title">How to fix</p>
          <p className="guidance-text">{finding.remediation}</p>
        </div>
      </div>
    </div>
  );
}

// The finding's file on GitHub, at the scanned commit. A file inside a .zip links to the archive.
function githubFileUrl(repository, ref, path, line) {
  if (!repository || !ref || !path) return '';
  const zipAt = path.toLowerCase().indexOf('.zip/');
  const file = zipAt >= 0 ? path.slice(0, zipAt + 4) : path;
  const encoded = file.split('/').map(encodeURIComponent).join('/');
  return `https://github.com/${repository}/blob/${encodeURIComponent(ref)}/${encoded}${zipAt >= 0 ? '' : `#L${line}`}`;
}

// Same order as the scan's findings table: most severe first, then by file and line.
function orderFindings(items) {
  return [...items].sort(
    (a, b) =>
      (SEVERITY_ORDER[b.finding.severity] || 0) - (SEVERITY_ORDER[a.finding.severity] || 0) ||
      a.finding.file.localeCompare(b.finding.file) ||
      a.finding.line - b.finding.line,
  );
}

function FindingDetail() {
  const { scanId, findingId } = useParams();
  const [detail, setDetail] = useState(null);
  const [active, setActive] = useState(null);
  const [error, setError] = useState('');

  const [reloadKey, setReloadKey] = useState(0);
  const [siblings, setSiblings] = useState([]);
  const [scan, setScan] = useState(null);
  const notify = useToast();

  // The scan (for the GitHub link) and its findings (for previous / next). Optional: the page works without them.
  useEffect(() => {
    let current = true;
    Promise.all([scanService.getScan(scanId), scanService.getFindings(scanId)])
      .then(([scanData, items]) => {
        if (!current) return;
        setScan(scanData);
        setSiblings(orderFindings(items));
      })
      .catch(() => {});
    return () => {
      current = false;
    };
  }, [scanId]);

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
      .catch((err) => {
        if (!current) return;
        setError(err.message);
        notify({ tone: 'danger', title: 'Could not load this finding', message: err.message });
      });
    return () => {
      current = false;
    };
  }, [scanId, findingId, reloadKey, notify]);

  // Load the neighbouring findings in the background, so the previous / next buttons open instantly.
  useEffect(() => {
    const index = siblings.findIndex((item) => item.finding_id === findingId);
    if (index < 0) return;
    [siblings[index - 1], siblings[index + 1]].filter(Boolean).forEach((item) => {
      scanService.getFinding(scanId, item.finding_id).catch(() => {});
    });
  }, [siblings, scanId, findingId]);

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

  const position = siblings.findIndex((item) => item.finding_id === findingId);
  const prev = position > 0 ? siblings[position - 1] : null;
  const next = position >= 0 && position < siblings.length - 1 ? siblings[position + 1] : null;
  const githubHref = githubFileUrl(detail.repository, scan?.commit || scan?.ref, detail.file_path, finding.line);

  const copyLocation = async () => {
    const location = `${detail.file_path}:${finding.line}`;
    try {
      await navigator.clipboard.writeText(location);
      notify({ tone: 'success', title: 'Location copied', message: location });
    } catch {
      notify({ tone: 'warning', title: 'Could not copy', message: 'Your browser blocked clipboard access.' });
    }
  };

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
        actions={
          <>
            <Button icon={ArrowLeft} to={`/scans/${scanId}`}>
              Back to scan
            </Button>
            {githubHref ? (
              <Button icon={ExternalLink} href={githubHref} target="_blank" rel="noopener noreferrer">
                View on GitHub
              </Button>
            ) : null}
            {siblings.length > 1 && position >= 0 ? (
              <div className="pager" role="group" aria-label="Findings in this scan">
                <Button
                  icon={ChevronLeft}
                  to={prev ? `/scans/${scanId}/findings/${prev.finding_id}` : undefined}
                  disabled={!prev}
                  aria-label="Previous finding"
                  title="Previous finding"
                />
                <span className="pager-count">
                  {position + 1} of {siblings.length}
                </span>
                <Button
                  icon={ChevronRight}
                  to={next ? `/scans/${scanId}/findings/${next.finding_id}` : undefined}
                  disabled={!next}
                  aria-label="Next finding"
                  title="Next finding"
                />
              </div>
            ) : null}
          </>
        }
      />

      <Panel
        title="What CryptoAudit found"
        actions={
          <Button size="sm" variant="ghost" icon={Copy} onClick={copyLocation}>
            Copy location
          </Button>
        }
      >
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
