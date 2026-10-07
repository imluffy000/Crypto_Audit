import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { BarChart3, Download, Plus } from 'lucide-react';
import DashboardLayout from '../layouts/DashboardLayout';
import EmptyState from '../components/EmptyState';
import { scanService } from '../services/scanService';

const STATUS_CLASS = { COMPLETED: 'success', FAILED: 'danger', RUNNING: 'pending', QUEUED: 'pending' };

function Reports() {
  const navigate = useNavigate();
  const [scans, setScans] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    scanService.listScans().then(setScans).catch((err) => setError(err.message));
  }, []);

  return (
    <DashboardLayout>
      <div className="page-header">
        <div>
          <p className="eyebrow">Scans & reports</p>
          <h1>Your scans</h1>
        </div>
        <button type="button" className="primary-button" onClick={() => navigate('/repositories/github')}>
          <Plus size={16} /> New scan
        </button>
      </div>

      {error ? <div className="form-error">{error}</div> : null}

      {scans && !scans.length ? (
        <EmptyState
          title="No scans yet."
          description="Choose a GitHub repository to run your first CryptoAudit scan."
          actionText="Choose repository"
          onAction={() => navigate('/repositories/github')}
        />
      ) : null}

      {scans?.length ? (
        <div className="card-panel">
          <h2>
            <BarChart3 size={17} /> Scan history
          </h2>
          <div className="findings-table scans">
            <div className="findings-row header">
              <span>Repository</span>
              <span>Branch</span>
              <span>Status</span>
              <span>Started</span>
              <span>Report</span>
            </div>
            {scans.map((scan) => (
              <div key={scan.scan_id} className="findings-row">
                <Link to={`/scans/${scan.scan_id}`}>
                  <strong>{scan.repository}</strong>
                </Link>
                <span>
                  <code>{scan.ref}</code>
                </span>
                <span className={`status-pill ${STATUS_CLASS[scan.status] || ''}`}>{scan.status.toLowerCase()}</span>
                <span>{new Date(scan.created_at).toLocaleString()}</span>
                <span>
                  {scan.status === 'COMPLETED' ? (
                    <a className="inline-link" href={scanService.reportUrl(scan.scan_id)}>
                      <Download size={13} /> Markdown
                    </a>
                  ) : (
                    '–'
                  )}
                </span>
              </div>
            ))}
          </div>
        </div>
      ) : null}
    </DashboardLayout>
  );
}

export default Reports;
