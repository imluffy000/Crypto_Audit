import { useCallback, useEffect, useState } from 'react';
import { Navigate } from 'react-router-dom';
import { ShieldAlert } from 'lucide-react';
import DashboardLayout from '../layouts/DashboardLayout';
import PageHeader from '../components/ui/PageHeader';
import Button from '../components/ui/Button';
import { EmptyState, ErrorState, LoadingState } from '../components/ui/States';
import { scanService } from '../services/scanService';

// /findings shows the findings of the most recent completed scan.
function LatestFindings() {
  const [target, setTarget] = useState(undefined);
  const [error, setError] = useState('');

  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let active = true;
    scanService
      .listScans()
      .then((scans) => active && setTarget(scans.find((scan) => scan.status === 'COMPLETED')?.scan_id || null))
      .catch((err) => active && setError(err.message));
    return () => {
      active = false;
    };
  }, [reloadKey]);

  const reload = useCallback(() => {
    setError('');
    setTarget(undefined);
    setReloadKey((key) => key + 1);
  }, []);

  if (target) return <Navigate to={`/scans/${target}`} replace />;

  return (
    <DashboardLayout>
      <PageHeader title="Findings" description="Findings from your most recent completed scan." />
      {error ? <ErrorState title="Could not load your scans" message={error} onRetry={reload} /> : null}
      {!error && target === undefined ? <LoadingState rows={4} label="Finding your latest scan" /> : null}
      {target === null ? (
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
    </DashboardLayout>
  );
}

export default LatestFindings;
