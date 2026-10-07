import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { FolderGit2, ShieldCheck, X } from 'lucide-react';
import DashboardLayout from '../layouts/DashboardLayout';
import RepositoryTree from '../components/RepositoryTree';
import PageHeader, { SectionHeader } from '../components/ui/PageHeader';
import Button from '../components/ui/Button';
import Badge from '../components/ui/Badge';
import FilterBar, { SearchBar } from '../components/ui/FilterBar';
import { Alert, EmptyState } from '../components/ui/States';
import { useToast } from '../components/ui/toastContext';
import { useAuth } from '../context/AppContext';
import { scanService } from '../services/scanService';
import { formatMegabytes, pluralize } from '../utils/format';

const PIPELINE = [
  ['Analysis', 'CR1–CR5 rules over every Python file'],
  ['Context', 'Enclosing function, imports and in-module callers of each finding'],
  ['Repair', 'S1–S2 deterministic candidates; S3–S4 when a language model is available'],
  ['Validation', 'Integrity checks and scanner re-scan; behavioural gates need an oracle'],
];

function RepositoryDetails() {
  const navigate = useNavigate();
  const notify = useToast();
  const { selectedRepository, setSelectedRepository } = useAuth();
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState('');
  const [query, setQuery] = useState('');

  if (!selectedRepository) {
    return (
      <DashboardLayout>
        <PageHeader breadcrumbs={[{ label: 'Repositories', to: '/repositories/github' }, { label: 'Review' }]} title="Review repository" />
        <EmptyState
          icon={FolderGit2}
          title="No repository selected"
          description="Choose a GitHub repository, or open local files for review."
          action={
            <Button variant="primary" to="/repositories/github">
              Choose a repository
            </Button>
          }
        />
      </DashboardLayout>
    );
  }

  const repo = selectedRepository;
  const isGitHub = repo.source === 'GitHub';

  const startScan = async () => {
    setStarting(true);
    setError('');
    try {
      const { scan_id: scanId } = await scanService.startScan(repo);
      notify({ tone: 'success', title: 'Scan started', message: `${repo.fullName || repo.name} is queued for analysis.` });
      navigate(`/scans/${scanId}`);
    } catch (err) {
      setError(err.message);
      notify({ tone: 'danger', title: 'Scan could not be started', message: err.message });
      setStarting(false);
    }
  };

  const clearSelection = () => {
    setSelectedRepository(null);
    notify({ tone: 'info', title: 'Selection cleared', message: 'Choose another repository to scan.' });
    navigate('/repositories/github');
  };

  const details = [
    ['Source', isGitHub ? 'GitHub' : 'Local files'],
    ['Branch', <span key="b" className="mono">{repo.branch || 'main'}</span>],
    ['Files', repo.files ?? '–'],
    ['Python files', repo.archives ? `${repo.pythonFiles ?? 0} + inside ${pluralize(repo.archives, 'zip archive')}` : repo.pythonFiles ?? '–'],
    ['Size', formatMegabytes(repo.totalSize)],
    ['Status', isGitHub ? <Badge key="s" tone="success">Ready to scan</Badge> : <Badge key="s" tone="neutral">Review only</Badge>],
  ];

  return (
    <DashboardLayout>
      <PageHeader
        breadcrumbs={[{ label: 'Repositories', to: isGitHub ? '/repositories/github' : '/repositories/upload' }, { label: 'Review' }]}
        title={repo.fullName || repo.name}
        mono
        description={isGitHub ? 'Check the repository before starting a scan.' : 'Local files are shown for review only.'}
        actions={
          <>
            <Button variant="ghost" icon={X} onClick={clearSelection}>
              Clear selection
            </Button>
            <Button variant="primary" icon={ShieldCheck} onClick={startScan} loading={starting} disabled={!isGitHub}>
              {starting ? 'Starting scan…' : 'Start scan'}
            </Button>
          </>
        }
      />

      {error ? (
        <Alert tone="danger" title="The scan could not be started">
          {error}
        </Alert>
      ) : null}
      {!isGitHub ? (
        <Alert tone="warning" title="Scanning needs a GitHub repository">
          Local uploads can be reviewed here, but scans fetch code from GitHub so results are tied to a commit.
        </Alert>
      ) : null}

      {isGitHub && repo.archives ? (
        <Alert tone="info" title={`${pluralize(repo.archives, 'zip archive')} found`}>
          Python files inside <span className="mono">.zip</span> archives are scanned too. They are read in memory, one level deep,
          and never extracted or executed. Their findings appear as <span className="mono">archive.zip/path/file.py</span>.
        </Alert>
      ) : null}

      <dl className="definition-grid">
        {details.map(([term, value]) => (
          <div key={term}>
            <dt>{term}</dt>
            <dd>{value}</dd>
          </div>
        ))}
      </dl>

      <div className="review-grid">
        <section aria-labelledby="files-heading">
          <SectionHeader id="files-heading" title="Files" description={repo.truncated ? 'The tree is truncated for display. The scan still reads every Python file within the configured limits.' : null} />
          <FilterBar>
            <SearchBar value={query} onChange={setQuery} placeholder="Filter by file name" label="Filter files" />
          </FilterBar>
          <div className="tree-frame">
            <RepositoryTree tree={repo.tree || { name: repo.name, type: 'folder', children: [] }} searchQuery={query} />
          </div>
        </section>

        {isGitHub ? (
          <aside aria-labelledby="pipeline-heading" className="review-side">
            <SectionHeader id="pipeline-heading" title="What the scan does" as="h2" />
            <ol className="pipeline-steps">
              {PIPELINE.map(([title, text], index) => (
                <li key={title}>
                  <span className="pipeline-index">{index + 1}</span>
                  <div>
                    <p className="pipeline-title">{title}</p>
                    <p className="pipeline-text">{text}</p>
                  </div>
                </li>
              ))}
            </ol>
            <p className="muted small">Repository code is never executed. Without a test oracle the best possible verdict is “Unverified”.</p>
          </aside>
        ) : null}
      </div>
    </DashboardLayout>
  );
}

export default RepositoryDetails;
