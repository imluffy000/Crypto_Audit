import { useCallback, useEffect, useMemo, useState } from 'react';
import { useParams } from 'react-router-dom';
import { ChevronDown, Download, ShieldCheck } from 'lucide-react';
import DashboardLayout from '../layouts/DashboardLayout';
import StageList from '../components/StageList';
import VerdictBadge from '../components/VerdictBadge';
import PageHeader, { SectionHeader } from '../components/ui/PageHeader';
import Button from '../components/ui/Button';
import { SeverityBadge } from '../components/ui/Badge';
import DataTable from '../components/ui/DataTable';
import FilterBar, { SearchBar, Select } from '../components/ui/FilterBar';
import StatusIndicator from '../components/ui/StatusIndicator';
import { Alert, EmptyState, ErrorState, LoadingState } from '../components/ui/States';
import { scanService } from '../services/scanService';
import { formatDateTime, humanize, pluralize, RULE_NAMES, SEVERITY_ORDER, VERDICT_ORDER } from '../utils/format';

const POLL_MS = 1500;
const FINISHED = ['COMPLETED', 'FAILED'];
const VERDICTS = ['VERIFIED', 'UNVERIFIED', 'FAILED', 'NO_CANDIDATE'];

function SummaryMetrics({ scan }) {
  const { summary } = scan;
  return (
    <dl className="metric-grid">
      <div className="metric">
        <dt>Python files scanned</dt>
        <dd>
          <span className="metric-value">{summary.files_scanned}</span>
          {scan.skipped_files.length ? <span className="metric-detail">{scan.skipped_files.length} skipped</span> : null}
        </dd>
      </div>
      <div className="metric">
        <dt>Findings</dt>
        <dd>
          <span className="metric-value">{summary.findings}</span>
          <span className="metric-detail">in {pluralize(summary.files_with_findings, 'file')}</span>
        </dd>
      </div>
      <div className="metric">
        <dt>Strategies run</dt>
        <dd>
          <span className="metric-value">{scan.strategies.length}</span>
          <span className="metric-detail mono">{scan.strategies.join(' · ') || 'none'}</span>
        </dd>
      </div>
      <div className="metric">
        <dt>Scanner-clean, not verified</dt>
        <dd>
          <span className="metric-value">{summary.scanner_clean_not_verified}</span>
          <span className="metric-detail">Scanner silence is not proof of a fix</span>
        </dd>
      </div>
    </dl>
  );
}

// Candidate counts per strategy (one candidate per file), straight from the scan summary.
function StrategyOutcomes({ summary, strategies }) {
  const rows = strategies.filter((strategy) => summary.verdicts_by_strategy[strategy]);
  if (!rows.length) return null;
  return (
    <section aria-labelledby="outcomes-heading">
      <SectionHeader id="outcomes-heading" title="Repair outcomes by strategy" description="One candidate per affected file and strategy." />
      <div className="table-scroll bordered">
        <table className="simple-table">
          <thead>
            <tr>
              <th scope="col">Strategy</th>
              {VERDICTS.map((verdict) => (
                <th key={verdict} scope="col" className="align-end">
                  {humanize(verdict)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((strategy) => (
              <tr key={strategy}>
                <th scope="row" className="mono">
                  {strategy}
                </th>
                {VERDICTS.map((verdict) => (
                  <td key={verdict} className="align-end tabular">
                    {summary.verdicts_by_strategy[strategy][verdict] || <span className="muted">0</span>}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function FindingsTable({ scanId, findings, strategies }) {
  const [query, setQuery] = useState('');
  const [rule, setRule] = useState('all');
  const [severity, setSeverity] = useState('all');
  const [verdict, setVerdict] = useState('all');

  const rules = useMemo(() => [...new Set(findings.map((item) => item.finding.rule_id))].sort(), [findings]);
  const filtered = useMemo(() => {
    const term = query.trim().toLowerCase();
    return findings.filter(
      ({ finding, best_verdict: best }) =>
        (!term || `${finding.file} ${finding.explanation} ${finding.matched_api}`.toLowerCase().includes(term)) &&
        (rule === 'all' || finding.rule_id === rule) &&
        (severity === 'all' || finding.severity === severity) &&
        (verdict === 'all' || best === verdict),
    );
  }, [findings, query, rule, severity, verdict]);

  const columns = [
    {
      key: 'severity',
      header: 'Severity',
      sortValue: (item) => SEVERITY_ORDER[item.finding.severity] || 0,
      render: (item) => <SeverityBadge severity={item.finding.severity} />,
    },
    {
      key: 'location',
      header: 'Location',
      primary: true,
      sortValue: (item) => `${item.finding.file}:${String(item.finding.line).padStart(6, '0')}`,
      render: (item) => (
        <span className="mono location">
          {item.finding.file}
          <span className="muted">:{item.finding.line}</span>
        </span>
      ),
    },
    {
      key: 'rule',
      header: 'Rule',
      sortValue: (item) => item.finding.rule_id,
      render: (item) => (
        <span className="rule-cell" title={RULE_NAMES[item.finding.rule_id]}>
          <span className="mono">{item.finding.rule_id}</span>
        </span>
      ),
    },
    { key: 'issue', header: 'Issue', className: 'cell-wrap', render: (item) => <span className="clamp-2">{item.finding.explanation}</span> },
    {
      key: 'best',
      header: 'Best result',
      sortValue: (item) => VERDICT_ORDER[item.best_verdict] || 0,
      render: (item) => <VerdictBadge verdict={item.best_verdict} />,
    },
    ...strategies.map((strategy) => ({
      key: `strategy-${strategy}`,
      header: strategy,
      align: 'center',
      className: 'cell-strategy',
      render: (item) => (item.verdicts[strategy] ? <VerdictBadge verdict={item.verdicts[strategy]} compact /> : <span className="muted">–</span>),
    })),
  ];

  return (
    <section aria-labelledby="findings-heading">
      <SectionHeader id="findings-heading" title="Findings" description="Select a finding to compare the original code with each repair candidate." />
      <FilterBar summary={filtered.length === findings.length ? pluralize(findings.length, 'finding') : `${filtered.length} of ${findings.length} findings`}>
        <SearchBar value={query} onChange={setQuery} placeholder="Search file, API or description" label="Search findings" />
        <Select label="Rule" value={rule} onChange={setRule} options={[{ value: 'all', label: 'All rules' }, ...rules.map((id) => ({ value: id, label: `${id} · ${RULE_NAMES[id] || id}` }))]} />
        <Select
          label="Severity"
          value={severity}
          onChange={setSeverity}
          options={[{ value: 'all', label: 'All severities' }, ...['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'].map((s) => ({ value: s, label: humanize(s) }))]}
        />
        <Select label="Best result" value={verdict} onChange={setVerdict} options={[{ value: 'all', label: 'All results' }, ...VERDICTS.map((v) => ({ value: v, label: humanize(v) }))]} />
      </FilterBar>
      <DataTable
        caption="Findings"
        columns={columns}
        rows={filtered}
        rowKey={(item) => item.finding_id}
        rowHref={(item) => `/scans/${scanId}/findings/${item.finding_id}`}
        initialSort={{ key: 'severity', direction: 'desc' }}
        empty={<EmptyState compact title="No findings match" description="Try a different search or clear the filters." />}
      />
    </section>
  );
}

function ScanResults() {
  const { scanId } = useParams();
  const [scan, setScan] = useState(null);
  const [findings, setFindings] = useState(null);
  const [error, setError] = useState('');
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let cancelled = false;
    let timer;
    const poll = async () => {
      try {
        const next = await scanService.getScan(scanId);
        if (cancelled) return;
        setScan(next);
        setError('');
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
  }, [scanId, attempt]);

  const retry = useCallback(() => setAttempt((n) => n + 1), []);

  const meta = scan ? (
    <>
      <StatusIndicator status={scan.status} />
      <span>
        Branch <span className="mono">{scan.ref}</span>
      </span>
      {scan.commit ? (
        <span>
          Commit <span className="mono">{scan.commit.slice(0, 10)}</span>
        </span>
      ) : null}
      <span>Started {formatDateTime(scan.created_at)}</span>
    </>
  ) : null;

  return (
    <DashboardLayout>
      <PageHeader
        breadcrumbs={[{ label: 'Scans', to: '/reports' }, { label: scan?.repository || 'Scan' }]}
        title={scan?.repository || 'Scan'}
        mono
        meta={meta}
        actions={
          scan?.status === 'COMPLETED' ? (
            <Button icon={Download} href={scanService.reportUrl(scanId)}>
              Download report
            </Button>
          ) : null
        }
      />

      {error ? <ErrorState title="Could not load this scan" message={error} onRetry={retry} /> : null}
      {!scan && !error ? <LoadingState variant="metrics" rows={4} label="Loading scan" /> : null}

      {scan && scan.status !== 'COMPLETED' ? (
        <section className="progress-panel" aria-labelledby="progress-heading" aria-live="polite">
          <SectionHeader
            id="progress-heading"
            title={scan.status === 'FAILED' ? 'Scan failed' : 'Scan in progress'}
            description={scan.status === 'FAILED' ? null : 'This page updates automatically. You can leave and come back later.'}
          />
          {scan.status === 'FAILED' ? (
            <Alert tone="danger" title={scan.error?.code ? humanize(String(scan.error.code)) : 'The scan stopped'}>
              {scan.error?.message || 'No further detail was recorded.'}
            </Alert>
          ) : null}
          <StageList stages={scan.stages} />
        </section>
      ) : null}

      {scan?.summary ? (
        <>
          <SummaryMetrics scan={scan} />

          {Object.entries(scan.skipped_strategies).length ? (
            <Alert tone="warning" title="Some repair strategies did not run">
              <ul className="bullet-list">
                {Object.entries(scan.skipped_strategies).map(([strategy, reason]) => (
                  <li key={strategy}>
                    <span className="mono">{strategy}</span>: {reason}
                  </li>
                ))}
              </ul>
            </Alert>
          ) : null}

          {findings === null ? <LoadingState rows={5} label="Loading findings" /> : null}
          {findings && findings.length ? <FindingsTable scanId={scanId} findings={findings} strategies={scan.strategies} /> : null}
          {findings && !findings.length ? (
            <EmptyState
              icon={ShieldCheck}
              title="No cryptographic misuse found"
              description="The CR1–CR5 rules did not flag any scanned Python file. This means no known misuse pattern matched — not that the code is proven secure."
            />
          ) : null}

          <StrategyOutcomes summary={scan.summary} strategies={scan.strategies} />

          {scan.skipped_files.length ? (
            <details className="disclosure">
              <summary>
                <ChevronDown size={14} aria-hidden="true" className="disclosure-icon" />
                {pluralize(scan.skipped_files.length, 'skipped file')}
              </summary>
              <ul className="skipped-list">
                {scan.skipped_files.map((file) => (
                  <li key={file.path}>
                    <span className="mono">{file.path}</span>
                    <span className="muted">{file.reason}</span>
                  </li>
                ))}
              </ul>
            </details>
          ) : null}
        </>
      ) : null}
    </DashboardLayout>
  );
}

export default ScanResults;
