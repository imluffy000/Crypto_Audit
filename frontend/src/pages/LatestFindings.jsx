import { useEffect, useState } from 'react';
import { Navigate } from 'react-router-dom';
import DashboardLayout from '../layouts/DashboardLayout';
import EmptyState from '../components/EmptyState';
import { scanService } from '../services/scanService';

// /findings shows the findings of the most recent completed scan.
function LatestFindings() {
  const [target, setTarget] = useState(undefined);

  useEffect(() => {
    scanService
      .listScans()
      .then((scans) => setTarget(scans.find((scan) => scan.status === 'COMPLETED')?.scan_id || null))
      .catch(() => setTarget(null));
  }, []);

  if (target) return <Navigate to={`/scans/${target}`} replace />;

  return (
    <DashboardLayout>
      {target === null ? (
        <EmptyState
          title="No completed scans yet."
          description="Findings appear here once a scan of one of your repositories completes."
          actionText="Start a scan"
          onAction={() => window.location.assign('#/repositories/github')}
        />
      ) : (
        <p className="subtitle">Loading…</p>
      )}
    </DashboardLayout>
  );
}

export default LatestFindings;
