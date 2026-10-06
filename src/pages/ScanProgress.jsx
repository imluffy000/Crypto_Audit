import { useNavigate } from 'react-router-dom';
import DashboardLayout from '../layouts/DashboardLayout';

function ScanProgress() {
  const navigate = useNavigate();

  return (
    <DashboardLayout>
      <div className="page-header">
        <div>
          <p className="eyebrow">Security Analysis</p>
          <h1>Scan initiated</h1>
        </div>
      </div>

      <div className="card-panel empty-state large">
        <div className="empty-icon">◎</div>
        <h3>Security scanning functionality will be implemented in the next phase.</h3>
        <p>For this frontend-only version, the scan button transitions to a placeholder state instead of running any scanner or LLM workflow.</p>
        <button type="button" className="primary-button" onClick={() => navigate('/repositories/review')}>
          Back to Repository
        </button>
      </div>
    </DashboardLayout>
  );
}

export default ScanProgress;
