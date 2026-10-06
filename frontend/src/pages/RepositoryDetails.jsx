import { useNavigate } from 'react-router-dom';
import { ArrowLeft, CircleCheckBig, FolderTree, ShieldCheck } from 'lucide-react';
import DashboardLayout from '../layouts/DashboardLayout';
import RepositoryTree from '../components/RepositoryTree';
import { useAuth } from '../context/AppContext';
import { scanService } from '../services/scanService';

function RepositoryDetails() {
  const navigate = useNavigate();
  const { selectedRepository, setSelectedRepository } = useAuth();

  if (!selectedRepository) {
    return (
      <DashboardLayout>
        <div className="empty-state">
          <h3>No repository selected</h3>
          <p>Upload a repository or connect a GitHub repository to continue.</p>
        </div>
      </DashboardLayout>
    );
  }

  const handleStartScan = async () => {
    await scanService.prepareScan(selectedRepository);
    navigate('/scan/preparing');
  };

  return (
    <DashboardLayout>
      <div className="page-header review-header">
        <div>
          <p className="eyebrow">Review Repository</p>
          <h1>{selectedRepository.name}</h1>
        </div>
        <div className="header-actions small-gap">
          <button type="button" className="secondary-button" onClick={() => navigate(-1)}>
            <ArrowLeft size={14} /> Back
          </button>
          <button type="button" className="ghost-button" onClick={() => setSelectedRepository(null)}>
            Remove Repository
          </button>
        </div>
      </div>

      <div className="review-summary card-panel">
        <div className="review-metrics">
          <div>
            <span>Repository</span>
            <strong>{selectedRepository.name}</strong>
          </div>
          <div>
            <span>Source</span>
            <strong>{selectedRepository.source || 'Local Upload'}</strong>
          </div>
          <div>
            <span>Branch</span>
            <strong>{selectedRepository.branch || 'main'}</strong>
          </div>
          <div>
            <span>Files</span>
            <strong>{selectedRepository.files || 142}</strong>
          </div>
          <div>
            <span>Total Size</span>
            <strong>{selectedRepository.totalSize ? `${(selectedRepository.totalSize / (1024 * 1024)).toFixed(1)} MB` : '4.8 MB'}</strong>
          </div>
          <div>
            <span>Status</span>
            <strong className="success-text"><CircleCheckBig size={14} /> Ready for scanning</strong>
          </div>
        </div>
      </div>

      <div className="card-panel">
        <div className="panel-header-row">
          <h2>
            <FolderTree size={17} /> Complete repository structure captured
          </h2>
        </div>
        <RepositoryTree tree={selectedRepository.tree || { name: selectedRepository.name, type: 'folder', children: [] }} />
      </div>

      <div className="footer-actions">
        <button type="button" className="primary-button" onClick={handleStartScan}>
          <ShieldCheck size={16} /> Start Security Scan
        </button>
      </div>
    </DashboardLayout>
  );
}

export default RepositoryDetails;
