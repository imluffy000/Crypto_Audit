import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { AlertTriangle, ArrowLeft, CircleCheckBig, FolderTree, ShieldCheck } from 'lucide-react';
import DashboardLayout from '../layouts/DashboardLayout';
import RepositoryTree from '../components/RepositoryTree';
import { useAuth } from '../context/AppContext';
import { scanService } from '../services/scanService';

function RepositoryDetails() {
  const navigate = useNavigate();
  const { selectedRepository, setSelectedRepository } = useAuth();
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState('');

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

  const isGitHub = selectedRepository.source === 'GitHub';

  const handleStartScan = async () => {
    setStarting(true);
    setError('');
    try {
      const { scan_id: scanId } = await scanService.startScan(selectedRepository);
      navigate(`/scans/${scanId}`);
    } catch (err) {
      setError(err.message);
      setStarting(false);
    }
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
            <strong>{selectedRepository.files ?? 0}</strong>
          </div>
          <div>
            <span>Python files</span>
            <strong>{selectedRepository.pythonFiles ?? '–'}</strong>
          </div>
          <div>
            <span>Total Size</span>
            <strong>{selectedRepository.totalSize ? `${(selectedRepository.totalSize / (1024 * 1024)).toFixed(1)} MB` : '–'}</strong>
          </div>
          <div>
            <span>Status</span>
            <strong className={isGitHub ? 'success-text' : ''}>
              {isGitHub ? <><CircleCheckBig size={14} /> Ready for scanning</> : 'Review only'}
            </strong>
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

      {!isGitHub ? (
        <div className="alert-box warning">
          <AlertTriangle size={15} />
          <div>
            <strong>Scanning needs a GitHub repository.</strong>
            <p>Local uploads can be reviewed here, but scans fetch code from GitHub so results are tied to a commit.</p>
          </div>
        </div>
      ) : null}
      {selectedRepository.truncated ? (
        <p className="subtitle">The file tree is truncated for display; the scan still reads every Python file (within limits).</p>
      ) : null}
      {error ? <div className="form-error">{error}</div> : null}

      <div className="footer-actions">
        <span className="subtitle">
          Runs CR1–CR5 analysis, generates S1–S4 repair candidates and validates them. Your code is never executed.
        </span>
        <button type="button" className="primary-button" onClick={handleStartScan} disabled={!isGitHub || starting}>
          <ShieldCheck size={16} /> {starting ? 'Starting…' : 'Start Security Scan'}
        </button>
      </div>
    </DashboardLayout>
  );
}

export default RepositoryDetails;
