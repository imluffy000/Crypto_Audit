import { useCallback, useEffect, useMemo, useState } from 'react';
import { History, ShieldAlert, ShieldCheck } from 'lucide-react';
import DashboardLayout from '../layouts/DashboardLayout';
import VerdictBadge from '../components/VerdictBadge';
import PageHeader from '../components/ui/PageHeader';
import Button from '../components/ui/Button';
import { SeverityBadge } from '../components/ui/Badge';
import DataTable from '../components/ui/DataTable';
import FilterBar, { SearchBar, Select } from '../components/ui/FilterBar';
import { EmptyState, ErrorState, LoadingState } from '../components/ui/States';
import { useToast } from '../components/ui/toastContext';
import { scanService } from '../services/scanService';
import { formatRelative, humanize, pluralize, RULE_NAMES, SEVERITY_ORDER, VERDICT_ORDER } from '../utils/format';

const MAX_REPOSITORIES = 20;
const VERDICTS = ['VERIFIED', 'UNVERIFIED', 'FAILED', 'NO_CANDIDATE'];

// The newest completed scan of each repository: older scans of the same repository are superseded.
function latestCompletedPerRepository(scans) {
  const latest = new Map();
  scans
    .filter((scan) => scan.status === 'COMPLETED')
    .forEach((scan) => {
      const current = latest.get(scan.repository);
      if (!current || new Date(scan.created_at) > new Date(current.created_at)) latest.set(scan.repository, scan);
    });
  return [...latest.values()].sort((a, b) => new Date(b.created_at) - new Date(a.created_at)).slice(0, MAX_REPOSITORIES);
}

/** /findings — every finding from the latest completed scan of each repository, in one filterable table. */
function Findings() {
  const notify = useToast();
  const [rows, setRows] = useState(null);
  const [scanCount, setScanCount] = useState(0);
  const [error, setError] = useState('');
  const [reloadKey, setReloadKey] = useState(0);
  const [query, setQuery] = useState('');
  const [repository, setRepository] = useState('all');
  const [rule, setRule] = useState('all');
  const [severity, setSeverity] = useState('all');
  const [verdict, setVerdict] = useState('all');

  useEffect(() => {
    let active = true;
    scanService
      .listScans()
      .then(async (scans) => {
        const latest = latestCompletedPerRepository(scans);
        const lists = await Promise.all(latest.map((scan) => scanService.getFindings(scan.scan_id)));
        if (!active) return;
        setScanCount(latest.length);
        setRows(
          latest.flatMap((scan, index) =>
            lists[index].map((item) => ({ ...item, scanId: scan.scan_id, repository: scan.repository, scannedAt: scan.created_at })),
          ),
        );
      })
      .catch((err) => {
        if (!active) return;
        setError(err.message);
        notify({ tone: 'danger', title: 'Could not load findings', message: err.message });
      });
    return () => {
      active = false;
    };
  }, [reloadKey, notify]);

  const reload = useCallback(() => {
    setError('');
    setRows(null);
    setReloadKey((key) => key + 1);
  }, []);

  const repositories = useMemo(() => [...new Set((rows || []).map((row) => row.repository))].sort(), [rows]);
  const rules = useMemo(() => [...new Set((rows || []).map((row) => row.finding.rule_id))].sort(), [rows]);

  const filtered = useMemo(() => {
    const term = query.trim().toLowerCase();
    return (rows || []).filter(
      (row) =>
        (!term || `${row.repository} ${row.finding.file} ${row.finding.explanation} ${row.finding.matched_api}`.toLowerCase().includes(term)) &&
        (repository === 'all' || row.repository === repository) &&
        (rule === 'all' || row.finding.rule_id === rule) &&
        (severity === 'all' || row.finding.severity === severity) &&
        (verdict === 'all' || row.best_verdict === verdict),
    );
  }, [rows, query, repository, rule, severity, verdict]);

  const columns = [
    {
      key: 'severity',
      header: 'Severity',
      sortValue: (row) => SEVERITY_ORDER[row.finding.severity] || 0,
      render: (row) => <SeverityBadge severity={row.finding.severity} />,
    },
    {
      key: 'location',
      header: 'Location',
      primary: true,
      sortValue: (row) => `${row.finding.file}:${String(row.finding.line).padStart(6, '0')}`,
      render: (row) => (
        <span className="mono location">
          {row.finding.file}
          <span className="muted">:{row.finding.line}</span>
        </span>
      ),
    },
    {
      key: 'repository',
      header: 'Repository',
      sortValue: (row) => row.repository.toLowerCase(),
      className: 'cell-nowrap',
      render: (row) => <span className="mono small">{row.repository}</span>,
    },
    {
      key: 'rule',
      header: 'Rule',
      sortValue: (row) => row.finding.rule_id,
      render: (row) => (
        <span className="mono" title={RULE_NAMES[row.finding.rule_id]}>
          {row.finding.rule_id}
        </span>
      ),
    },
    { key: 'issue', header: 'Issue', className: 'cell-wrap', render: (row) => <span className="clamp-2">{row.finding.explanation}</span> },
    {
      key: 'best',
      header: 'Best result',
      sortValue: (row) => VERDICT_ORDER[row.best_verdict] || 0,
      render: (row) => <VerdictBadge verdict={row.best_verdict} />,
    },
    {
      key: 'scanned',
      header: 'Scanned',
      sortValue: (row) => row.scannedAt,
      render: (row) => <time dateTime={row.scannedAt}>{formatRelative(row.scannedAt)}</time>,
    },
  ];

  return (
    <DashboardLayout>
      <PageHeader
        title="Findings"
        description="Cryptographic misuse found in the latest completed scan of each of your repositories."
        actions={
          <Button icon={History} to="/reports">
            All scans
          </Button>
        }
      />

      {error ? <ErrorState title="Could not load findings" message={error} onRetry={reload} /> : null}
      {!error && !rows ? <LoadingState rows={6} label="Loading findings" /> : null}

      {rows && !scanCount ? (
        <EmptyState
          icon={ShieldAlert}
          title="No completed scans yet"
          description="Findings appear here once a scan of one of your repositories completes."
          action={
            <Button variant="primary" to="/repositories/github">
              Start a scan
            </Button>
          }
        />
      ) : null}

      {rows && scanCount > 0 && rows.length === 0 ? (
        <EmptyState
          icon={ShieldCheck}
          title="No findings"
          description={`The CR1–CR5 rules did not flag anything in the latest scan of ${pluralize(scanCount, 'repository', 'repositories')}. No known misuse pattern matched — that is not proof the code is secure.`}
        />
      ) : null}

      {rows && rows.length ? (
        <>
          <FilterBar
            summary={
              filtered.length === rows.length
                ? `${pluralize(rows.length, 'finding')} in ${pluralize(repositories.length, 'repository', 'repositories')}`
                : `${filtered.length} of ${rows.length} findings`
            }
          >
            <SearchBar value={query} onChange={setQuery} placeholder="Search file, API, repository or description" label="Search findings" />
            {repositories.length > 1 ? (
              <Select
                label="Repository"
                value={repository}
                onChange={setRepository}
                options={[{ value: 'all', label: 'All repositories' }, ...repositories.map((name) => ({ value: name, label: name }))]}
              />
            ) : null}
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
            caption="Findings across repositories"
            columns={columns}
            rows={filtered}
            rowKey={(row) => `${row.scanId}-${row.finding_id}`}
            rowHref={(row) => `/scans/${row.scanId}/findings/${row.finding_id}`}
            initialSort={{ key: 'severity', direction: 'desc' }}
            empty={<EmptyState compact title="No findings match" description="Try a different search or clear the filters." />}
          />
        </>
      ) : null}
    </DashboardLayout>
  );
}

export default Findings;
