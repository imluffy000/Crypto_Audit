import { useCallback, useEffect, useMemo, useState } from 'react';
import { Download, History, Plus } from 'lucide-react';
import DashboardLayout from '../layouts/DashboardLayout';
import PageHeader from '../components/ui/PageHeader';
import Button from '../components/ui/Button';
import DataTable from '../components/ui/DataTable';
import FilterBar, { SearchBar, Select } from '../components/ui/FilterBar';
import StatusIndicator from '../components/ui/StatusIndicator';
import { EmptyState, ErrorState, LoadingState } from '../components/ui/States';
import { useToast } from '../components/ui/toastContext';
import { scanService } from '../services/scanService';
import { formatDateTime, pluralize } from '../utils/format';

function Reports() {
  const [scans, setScans] = useState(null);
  const [error, setError] = useState('');
  const [query, setQuery] = useState('');
  const [status, setStatus] = useState('all');

  const [reloadKey, setReloadKey] = useState(0);
  const notify = useToast();

  useEffect(() => {
    let active = true;
    scanService
      .listScans()
      .then((list) => active && setScans(list))
      .catch((err) => {
        if (!active) return;
        setError(err.message);
        notify({ tone: 'danger', title: 'Could not load your scans', message: err.message });
      });
    return () => {
      active = false;
    };
  }, [reloadKey, notify]);

  const reload = useCallback(() => {
    setError('');
    setScans(null);
    setReloadKey((key) => key + 1);
  }, []);

  const filtered = useMemo(() => {
    const term = query.trim().toLowerCase();
    return (scans || []).filter(
      (scan) =>
        (!term || `${scan.repository} ${scan.ref}`.toLowerCase().includes(term)) &&
        (status === 'all' || scan.status === status || (status === 'RUNNING' && scan.status === 'QUEUED')),
    );
  }, [scans, query, status]);

  const columns = [
    { key: 'repository', header: 'Repository', primary: true, sortValue: (scan) => scan.repository.toLowerCase(), render: (scan) => <span className="mono">{scan.repository}</span> },
    { key: 'ref', header: 'Branch', sortValue: (scan) => scan.ref, render: (scan) => <span className="mono small">{scan.ref}</span> },
    { key: 'status', header: 'Status', sortValue: (scan) => scan.status, render: (scan) => <StatusIndicator status={scan.status} /> },
    { key: 'created', header: 'Started', sortValue: (scan) => scan.created_at, render: (scan) => <time dateTime={scan.created_at}>{formatDateTime(scan.created_at)}</time> },
    {
      key: 'report',
      header: <span className="visually-hidden">Report</span>,
      align: 'end',
      render: (scan) =>
        scan.status === 'COMPLETED' ? (
          <Button
            size="sm"
            variant="ghost"
            icon={Download}
            href={scanService.reportUrl(scan.scan_id)}
            onClick={() => notify({ tone: 'info', title: 'Downloading report', message: `${scan.repository} · Markdown` })} aria-label={`Download Markdown report for ${scan.repository}`}>
            Report
          </Button>
        ) : null,
    },
  ];

  return (
    <DashboardLayout>
      <PageHeader
        title="Scans & reports"
        description="Every scan you have run, with downloadable Markdown reports for completed ones."
        actions={
          <Button variant="primary" icon={Plus} to="/repositories/github">
            New scan
          </Button>
        }
      />

      {error ? <ErrorState title="Could not load your scans" message={error} onRetry={reload} /> : null}
      {!error && !scans ? <LoadingState rows={6} label="Loading scans" /> : null}

      {scans && !scans.length ? (
        <EmptyState
          icon={History}
          title="No scans yet"
          description="Choose a GitHub repository to run your first scan."
          action={
            <Button variant="primary" to="/repositories/github">
              Choose a repository
            </Button>
          }
        />
      ) : null}

      {scans?.length ? (
        <>
          <FilterBar summary={filtered.length === scans.length ? pluralize(scans.length, 'scan') : `${filtered.length} of ${scans.length} scans`}>
            <SearchBar value={query} onChange={setQuery} placeholder="Search repository or branch" label="Search scans" />
            <Select
              label="Status"
              value={status}
              onChange={setStatus}
              options={[
                { value: 'all', label: 'All statuses' },
                { value: 'COMPLETED', label: 'Completed' },
                { value: 'RUNNING', label: 'Running or queued' },
                { value: 'FAILED', label: 'Failed' },
              ]}
            />
          </FilterBar>
          <DataTable
            caption="Scan history"
            columns={columns}
            rows={filtered}
            rowKey={(scan) => scan.scan_id}
            rowHref={(scan) => `/scans/${scan.scan_id}`}
            initialSort={{ key: 'created', direction: 'desc' }}
            empty={<EmptyState compact title="No scans match" description="Try a different search or status." />}
          />
        </>
      ) : null}
    </DashboardLayout>
  );
}

export default Reports;
