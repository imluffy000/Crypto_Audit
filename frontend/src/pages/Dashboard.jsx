import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { FolderGit2, ShieldCheck } from 'lucide-react';
import DashboardLayout from '../layouts/DashboardLayout';
import EmptyState from '../components/EmptyState';
import { useAuth } from '../context/AppContext';
import { authService } from '../services/authService';
import { scanService } from '../services/scanService';

const STATUS_CLASS = { COMPLETED: 'success', FAILED: 'danger', RUNNING: 'pending', QUEUED: 'pending' };

function Dashboard() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [scans, setScans] = useState([]);
  const [health, setHealth] = useState(null);

  useEffect(() => {
    scanService.listScans().then(setScans).catch(() => setScans([]));
    authService.health().then(setHealth).catch(() => setHealth(null));
  }, []);

  const completed = scans.filter((scan) => scan.status === 'COMPLETED');
  const running = scans.filter((scan) => scan.status === 'RUNNING' || scan.status === 'QUEUED');

  return (
    <DashboardLayout>
      <div className="page-header">
        <div>
          <p className="eyebrow">CryptoAudit dashboard</p>
          <h1>Welcome back, {user?.name?.split(' ')[0] || 'Developer'}</h1>
        </div>
        <div className="header-actions">
          <button type="button" className="primary-button" onClick={() => navigate('/repositories/github')}>
            <FolderGit2 size={16} /> Scan a GitHub repository
          </button>
        </div>
      </div>

      <div className="hero-banner">
        <div>
          <p className="eyebrow strong">How it works</p>
          <h2>Pick a repository → CR1–CR5 analysis → context → repair candidates → independent validation → explained results.</h2>
        </div>
      </div>

      <div className="stats-grid">
        <div className="stat-card">
          <span>Scans</span>
          <strong>{scans.length}</strong>
          <small>{running.length} in progress</small>
        </div>
        <div className="stat-card">
          <span>Completed</span>
          <strong>{completed.length}</strong>
          <small>{scans.length - completed.length - running.length} failed</small>
        </div>
        <div className="stat-card">
          <span>Repair strategies</span>
          <strong>{health?.llm_available ? 'S1–S4' : 'S1–S2'}</strong>
          <small>{health?.llm_available ? `LLM: ${health.llm_model}` : 'LLM strategies need local Ollama'}</small>
        </div>
        <div className="stat-card">
          <span>Code execution</span>
          <strong>Never</strong>
          <small>Repository code is only analysed</small>
        </div>
      </div>

      <div className="panel-header-row">
        <h2>Recent scans</h2>
        {scans.length ? <Link className="inline-link" to="/reports">View all</Link> : null}
      </div>

      {scans.length ? (
        <div className="card-panel">
          <div className="findings-table scans">
            {scans.slice(0, 5).map((scan) => (
              <Link key={scan.scan_id} className="findings-row" to={`/scans/${scan.scan_id}`}>
                <strong>{scan.repository}</strong>
                <span>
                  <code>{scan.ref}</code>
                </span>
                <span className={`status-pill ${STATUS_CLASS[scan.status] || ''}`}>{scan.status.toLowerCase()}</span>
                <span>{new Date(scan.created_at).toLocaleString()}</span>
              </Link>
            ))}
          </div>
        </div>
      ) : (
        <EmptyState
          title="No scans yet."
          description="Choose one of your GitHub repositories to start your first scan."
          actionText="Choose repository"
          onAction={() => navigate('/repositories/github')}
        />
      )}

      <div className="mini-panel">
        <div className="mini-panel-header">
          <ShieldCheck size={16} /> <span>Verdicts</span>
        </div>
        <ul className="status-list">
          <li><span className="dot success" /> Verified — functional, security and compatibility checks passed</li>
          <li><span className="dot pending" /> Unverified — plausible repair; security properties not tested</li>
          <li><span className="dot danger" /> Failed — a validation or integrity check failed</li>
        </ul>
      </div>
    </DashboardLayout>
  );
}

export default Dashboard;
