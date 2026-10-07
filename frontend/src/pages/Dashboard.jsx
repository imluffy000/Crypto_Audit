import { useCallback, useEffect, useMemo, useState } from 'react';
import { FolderGit2, History, Plus } from 'lucide-react';
import DashboardLayout from '../layouts/DashboardLayout';
import PageHeader, { SectionHeader } from '../components/ui/PageHeader';
import Panel from '../components/ui/Panel';
import Button from '../components/ui/Button';
import Badge from '../components/ui/Badge';
import DataTable from '../components/ui/DataTable';
import StatusIndicator from '../components/ui/StatusIndicator';
import { EmptyState, ErrorState, LoadingState } from '../components/ui/States';
import { useAuth } from '../context/AppContext';
import { authService } from '../services/authService';
import { scanService } from '../services/scanService';
import { formatRelative, RULE_NAMES } from '../utils/format';

const MAX_SUMMARIES = 12;

// Findings are counted from the most recent completed scan of each repository, so rescans don't double count.
// The scan list carries no summaries, so those scans are fetched individually (bounded).
function latestCompletedPerRepository(scans) {
  const latest = new Map();
  scans
    .filter((scan) => scan.status === 'COMPLETED')
    .forEach((scan) => {
      const current = latest.get(scan.repository);
      if (!current || new Date(scan.created_at) > new Date(current.created_at)) latest.set(scan.repository, scan);
    });
  return [...latest.values()].sort((a, b) => new Date(b.created_at) - new Date(a.created_at)).slice(0, MAX_SUMMARIES);
}

function Metric({ label, value, detail }) {
  return (
    <div className="metric">
      <dt>{label}</dt>
      <dd>
        <span className="metric-value">{value}</span>
        {detail ? <span className="metric-detail">{detail}</span> : null}
      </dd>
    </div>
  );
}

function EnvironmentList({ health }) {
  if (!health) return <p className="muted">Server status unavailable.</p>;
  const rows = [
    ['GitHub sign-in', health.github_configured ? <Badge key="g" tone="success">Configured</Badge> : <Badge key="g" tone="warning">Not configured</Badge>],
    ['Repository access', health.repo_access === 'public' ? 'Public repositories' : 'Public and private'],
    ['Repair strategies', health.llm_available ? 'S1 · S2 · S3 · S4' : 'S1 · S2 (S3/S4 need a language model)'],
    [
      'Language model',
      health.llm_available ? <span key="m" className="mono small">{health.llm_model}</span> : <Badge key="m" tone="neutral">Unavailable</Badge>,
    ],
    ['Code execution', 'Never — repository code is analysed statically'],
    ['Server version', <span key="v" className="mono small">{health.version}</span>],
  ];
  return (
    <dl className="definition-list">
      {rows.map(([term, value]) => (
        <div key={term}>
          <dt>{term}</dt>
          <dd>{value}</dd>
        </div>
      ))}
    </dl>
  );
}

function Dashboard() {
  const { user } = useAuth();
  const [scans, setScans] = useState(null);
  const [latest, setLatest] = useState(null);
  const [health, setHealth] = useState(null);
  const [error, setError] = useState('');

  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let active = true;
    scanService
      .listScans()
      .then(async (list) => {
        const details = await Promise.all(latestCompletedPerRepository(list).map((scan) => scanService.getScan(scan.scan_id)));
        if (!active) return;
        setScans(list);
        setLatest(details.filter((scan) => scan.summary));
      })
      .catch((err) => active && setError(err.message));
    authService
      .health()
      .then((data) => active && setHealth(data))
      .catch(() => active && setHealth(null));
    return () => {
      active = false;
    };
  }, [reloadKey]);

  const reload = useCallback(() => {
    setError('');
    setScans(null);
    setLatest(null);
    setReloadKey((key) => key + 1);
  }, []);

  const stats = useMemo(() => {
    if (!scans || !latest) return null;
    const byRule = {};
    latest.forEach((scan) =>
      Object.entries(scan.summary.findings_by_rule).forEach(([rule, count]) => {
        byRule[rule] = (byRule[rule] || 0) + count;
      }),
    );
    return {
      repositories: new Set(scans.map((scan) => scan.repository)).size,
      running: scans.filter((scan) => scan.status === 'RUNNING' || scan.status === 'QUEUED').length,
      failed: scans.filter((scan) => scan.status === 'FAILED').length,
      findings: latest.reduce((sum, scan) => sum + scan.summary.findings, 0),
      filesAffected: latest.reduce((sum, scan) => sum + scan.summary.files_with_findings, 0),
      byRule,
      latestCount: latest.length,
    };
  }, [scans, latest]);

  const firstName = user?.name?.split(' ')[0] || user?.login;
  const maxRule = stats ? Math.max(1, ...Object.values(stats.byRule)) : 1;

  const columns = [
    { key: 'repository', header: 'Repository', primary: true, render: (scan) => <span className="mono">{scan.repository}</span>, sortValue: (scan) => scan.repository },
    { key: 'status', header: 'Status', render: (scan) => <StatusIndicator status={scan.status} /> },
    { key: 'created', header: 'Started', align: 'end', render: (scan) => <time dateTime={scan.created_at}>{formatRelative(scan.created_at)}</time> },
  ];

  return (
    <DashboardLayout>
      <PageHeader
        title="Dashboard"
        description={firstName ? `Signed in as ${firstName}. Overview of your CryptoAudit scans.` : 'Overview of your CryptoAudit scans.'}
        actions={
          <Button variant="primary" icon={Plus} to="/repositories/github">
            New scan
          </Button>
        }
      />

      {error ? <ErrorState title="Could not load your scans" message={error} onRetry={reload} /> : null}

      {!error && !stats ? <LoadingState variant="metrics" rows={4} label="Loading dashboard" /> : null}

      {stats ? (
        <>
          <dl className="metric-grid">
            <Metric label="Repositories scanned" value={stats.repositories} />
            <Metric label="Scans" value={scans.length} detail={stats.running ? `${stats.running} in progress` : stats.failed ? `${stats.failed} failed` : null} />
            <Metric label="Open findings" value={stats.findings} detail={stats.latestCount ? 'latest scan per repository' : null} />
            <Metric label="Files affected" value={stats.filesAffected} />
          </dl>

          {scans.length ? (
            <div className="dashboard-grid">
              <section aria-labelledby="recent-scans" className="dashboard-main">
                <SectionHeader
                  id="recent-scans"
                  title="Recent scans"
                  actions={
                    <Button size="sm" variant="ghost" icon={History} to="/reports">
                      All scans
                    </Button>
                  }
                />
                <DataTable caption="Recent scans" columns={columns} rows={scans.slice(0, 6)} rowKey={(scan) => scan.scan_id} rowHref={(scan) => `/scans/${scan.scan_id}`} pageSize={null} />

                <SectionHeader title="Findings by rule" description="From the latest completed scan of each repository." />
                {Object.keys(stats.byRule).length ? (
                  <ul className="bar-list">
                    {Object.entries(stats.byRule)
                      .sort((a, b) => b[1] - a[1])
                      .map(([rule, count]) => (
                        <li key={rule}>
                          <span className="bar-label">
                            <span className="mono">{rule}</span> {RULE_NAMES[rule] || ''}
                          </span>
                          <span className="bar-track" aria-hidden="true">
                            <span className="bar-fill" style={{ width: `${(count / maxRule) * 100}%` }} />
                          </span>
                          <span className="bar-value">{count}</span>
                        </li>
                      ))}
                  </ul>
                ) : (
                  <p className="muted">{stats.latestCount ? 'No findings in your latest scans.' : 'No completed scans yet.'}</p>
                )}
              </section>

              <aside className="dashboard-side">
                <Panel title="Environment" headingLevel={2}>
                  <EnvironmentList health={health} />
                </Panel>
              </aside>
            </div>
          ) : (
            <EmptyState
              icon={FolderGit2}
              title="No scans yet"
              description="Choose one of your GitHub repositories. CryptoAudit checks it for CR1–CR5 cryptographic misuse, proposes repairs and validates them."
              action={
                <Button variant="primary" to="/repositories/github">
                  Choose a repository
                </Button>
              }
            />
          )}
        </>
      ) : null}
    </DashboardLayout>
  );
}

export default Dashboard;
