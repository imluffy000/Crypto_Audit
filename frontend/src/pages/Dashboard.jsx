import { useNavigate } from 'react-router-dom';
import { ArrowUpRight, FolderGit2, Plus, ShieldAlert, ShieldCheck, Sparkles } from 'lucide-react';
import DashboardLayout from '../layouts/DashboardLayout';
import EmptyState from '../components/EmptyState';
import RepositoryCard from '../components/RepositoryCard';
import { useAuth } from '../context/AppContext';
import { mockRepositories } from '../data/mockRepository';

function Dashboard() {
  const navigate = useNavigate();
  const { user, selectedRepository } = useAuth();

  const repoList = selectedRepository ? [selectedRepository] : mockRepositories.slice(0, 2);

  return (
    <DashboardLayout>
      <div className="page-header">
        <div>
          <p className="eyebrow">CryptoAudit dashboard</p>
          <h1>Welcome back, {user?.name?.split(' ')[0] || 'Developer'}</h1>
        </div>
        <div className="header-actions">
          <button type="button" className="primary-button" onClick={() => navigate('/repositories/upload')}>
            <Plus size={16} /> Upload Repository
          </button>
          <button type="button" className="secondary-button" onClick={() => navigate('/repositories/github')}>
            Connect GitHub Repository
          </button>
        </div>
      </div>

      <div className="hero-banner">
        <div>
          <p className="eyebrow strong">Welcome to CryptoAudit</p>
          <h2>Upload your repository or source files to begin a security audit.</h2>
        </div>
        <button type="button" className="primary-button" onClick={() => navigate('/repositories/upload')}>
          <Plus size={16} /> Add Repository
        </button>
      </div>

      <div className="stats-grid">
        <div className="stat-card">
          <span>Repositories</span>
          <strong>{selectedRepository ? '1 / 1' : '0 / mock'}</strong>
          <small>Selected repo</small>
        </div>
        <div className="stat-card muted">
          <span>Scans</span>
          <strong>Coming soon</strong>
          <small>Backend integration required</small>
        </div>
        <div className="stat-card muted">
          <span>Security Findings</span>
          <strong>Coming soon</strong>
          <small>Detection engine pending</small>
        </div>
        <div className="stat-card muted">
          <span>Reports</span>
          <strong>Coming soon</strong>
          <small>Risk reporting pending</small>
        </div>
      </div>

      <div className="panel-header-row">
        <h2>Recent Repositories</h2>
      </div>

      {repoList.length ? (
        <div className="repository-grid">
          {repoList.map((repo) => (
            <RepositoryCard
              key={repo.id || repo.name}
              repository={repo}
              onView={() => {
                navigate('/repositories/review');
              }}
            />
          ))}
        </div>
      ) : (
        <EmptyState
          title="No repository added yet."
          description="Add a local folder or connect a GitHub repository to begin the audit flow."
          actionText="Upload Repository"
          onAction={() => navigate('/repositories/upload')}
        />
      )}

      <div className="mini-panel">
        <div className="mini-panel-header">
          <ShieldCheck size={16} /> <span>Workflow status</span>
        </div>
        <ul className="status-list">
          <li><span className="dot success" /> Repository upload</li>
          <li><span className="dot success" /> Validation</li>
          <li><span className="dot pending" /> Scan engine</li>
          <li><span className="dot pending" /> AI review</li>
        </ul>
      </div>
    </DashboardLayout>
  );
}

export default Dashboard;
