import { useCallback, useEffect, useMemo, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { ArrowRight, ExternalLink, FolderGit2, Globe, Lock, RotateCw, Upload } from 'lucide-react';
import DashboardLayout from '../layouts/DashboardLayout';
import FileUpload from '../components/FileUpload';
import RepositoryTree from '../components/RepositoryTree';
import PageHeader, { SectionHeader } from '../components/ui/PageHeader';
import Button from '../components/ui/Button';
import Badge from '../components/ui/Badge';
import DataTable from '../components/ui/DataTable';
import FilterBar, { SearchBar, Select } from '../components/ui/FilterBar';
import Tabs, { TabPanel } from '../components/ui/Tabs';
import { Alert, EmptyState, ErrorState, LoadingState } from '../components/ui/States';
import { useToast } from '../components/ui/toastContext';
import { buildTreeFromFiles, normalizeFileEntry } from '../utils/fileUtils';
import { validateRepositoryFiles } from '../utils/validation';
import { formatMegabytes, pluralize } from '../utils/format';
import { authService } from '../services/authService';
import { repositoryService } from '../services/repositoryService';
import { useAuth } from '../context/AppContext';

const TABS_ID = 'repository-source';

function GitHubRepositories({ onSelect, selectingId, manageUrl, repoAccess }) {
  const [repos, setRepos] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState('');
  const [visibility, setVisibility] = useState('all');
  const [language, setLanguage] = useState('all');

  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let active = true;
    repositoryService
      .getGitHubRepositories()
      .then((list) => active && setRepos(list))
      .catch((err) => active && setError(err.message))
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, [reloadKey]);

  const load = useCallback(() => {
    setLoading(true);
    setError('');
    setReloadKey((key) => key + 1);
  }, []);

  const languages = useMemo(() => [...new Set((repos || []).map((repo) => repo.language).filter(Boolean))].sort(), [repos]);

  const filtered = useMemo(() => {
    const term = query.trim().toLowerCase();
    return (repos || []).filter(
      (repo) =>
        (!term || `${repo.fullName} ${repo.description || ''}`.toLowerCase().includes(term)) &&
        (visibility === 'all' || repo.visibility.toLowerCase() === visibility) &&
        (language === 'all' || repo.language === language),
    );
  }, [repos, query, visibility, language]);

  const columns = [
    {
      key: 'name',
      header: 'Repository',
      sortValue: (repo) => repo.fullName.toLowerCase(),
      render: (repo) => (
        <div className="repo-cell">
          <span className="repo-name mono">
            <span className="repo-owner">{repo.owner}/</span>
            {repo.name}
          </span>
          {repo.description ? <span className="repo-description">{repo.description}</span> : null}
        </div>
      ),
    },
    {
      key: 'visibility',
      header: 'Visibility',
      sortValue: (repo) => repo.visibility,
      render: (repo) => (
        <Badge tone="neutral" icon={repo.visibility === 'Private' ? Lock : Globe}>
          {repo.visibility}
        </Badge>
      ),
    },
    { key: 'language', header: 'Language', sortValue: (repo) => repo.language || '', render: (repo) => repo.language || <span className="muted">–</span> },
    { key: 'branch', header: 'Default branch', render: (repo) => <span className="mono small">{repo.branch}</span> },
    { key: 'updated', header: 'Updated', sortValue: (repo) => repo.updatedAt || '', render: (repo) => repo.lastUpdated },
    {
      key: 'action',
      header: <span className="visually-hidden">Action</span>,
      align: 'end',
      render: (repo) => (
        <Button
          size="sm"
          icon={ArrowRight}
          onClick={() => onSelect(repo)}
          loading={selectingId === repo.id}
          disabled={Boolean(selectingId)}
          aria-label={`Select ${repo.fullName}`}
        >
          Select
        </Button>
      ),
    },
  ];

  return (
    <>
      <SectionHeader
        title="Your GitHub repositories"
        description={
          repoAccess === 'public'
            ? 'This server is configured for public repositories only.'
            : 'Repositories you own, collaborate on, or can reach through an organisation.'
        }
        actions={
          <>
            {manageUrl ? (
              <Button size="sm" variant="ghost" icon={ExternalLink} href={manageUrl} target="_blank" rel="noreferrer">
                Manage GitHub access
              </Button>
            ) : null}
            <Button size="sm" icon={RotateCw} onClick={load} loading={loading} disabled={loading}>
              Refresh
            </Button>
          </>
        }
      />

      {error ? <ErrorState title="Could not load repositories" message={error} onRetry={load} /> : null}
      {!error && !repos ? <LoadingState rows={6} label="Loading repositories" /> : null}

      {repos && !error ? (
        repos.length ? (
          <>
            <FilterBar summary={filtered.length === repos.length ? pluralize(repos.length, 'repository', 'repositories') : `${filtered.length} of ${repos.length} repositories`}>
              <SearchBar value={query} onChange={setQuery} placeholder="Search repositories" label="Search repositories" />
              <Select
                label="Visibility"
                value={visibility}
                onChange={setVisibility}
                options={[
                  { value: 'all', label: 'All visibility' },
                  { value: 'public', label: 'Public' },
                  { value: 'private', label: 'Private' },
                ]}
              />
              <Select label="Language" value={language} onChange={setLanguage} options={[{ value: 'all', label: 'All languages' }, ...languages.map((lang) => ({ value: lang, label: lang }))]} />
            </FilterBar>
            <DataTable
              caption="GitHub repositories"
              columns={columns}
              rows={filtered}
              rowKey={(repo) => repo.id}
              initialSort={{ key: 'updated', direction: 'desc' }}
              empty={<EmptyState compact title="No repositories match" description="Try a different search or clear the filters." />}
            />
          </>
        ) : (
          <EmptyState
            icon={FolderGit2}
            title="No repositories found"
            description={
              manageUrl
                ? 'Organisation repositories may need an owner to approve CryptoAudit. Use “Manage GitHub access” to request it.'
                : 'Create or get access to a repository on GitHub, then refresh this list.'
            }
          />
        )
      ) : null}
    </>
  );
}

function LocalReview({ onReview }) {
  const [files, setFiles] = useState([]);
  const [query, setQuery] = useState('');
  const [extension, setExtension] = useState('all');
  const normalizedFiles = useMemo(() => files.map((file, index) => normalizeFileEntry(file, index)), [files]);
  const validation = useMemo(() => validateRepositoryFiles(normalizedFiles), [normalizedFiles]);
  const tree = useMemo(() => buildTreeFromFiles(normalizedFiles), [normalizedFiles]);

  return (
    <>
      <Alert tone="info" title="Local files can be reviewed, not scanned">
        Scans fetch code from GitHub so every result is tied to a commit. Use this to inspect a project's structure before pushing it.
      </Alert>
      <FileUpload onFilesSelected={setFiles} />

      {normalizedFiles.length ? (
        <section className="stack" aria-labelledby="local-summary">
          <SectionHeader
            id="local-summary"
            title={`${pluralize(normalizedFiles.length, 'file')} selected`}
            actions={
              <Button variant="primary" icon={ArrowRight} onClick={() => onReview(normalizedFiles, tree)}>
                Review files
              </Button>
            }
          />
          <dl className="metric-grid compact">
            <div className="metric">
              <dt>Total size</dt>
              <dd>
                <span className="metric-value">{formatMegabytes(validation.totalSize)}</span>
              </dd>
            </div>
            <div className="metric">
              <dt>Accepted</dt>
              <dd>
                <span className="metric-value">{validation.validFiles}</span>
              </dd>
            </div>
            <div className="metric">
              <dt>Need attention</dt>
              <dd>
                <span className={`metric-value ${validation.invalidFiles ? 'text-warning' : ''}`}>{validation.invalidFiles}</span>
              </dd>
            </div>
          </dl>

          {validation.invalidFiles ? (
            <Alert tone="warning" title={`${pluralize(validation.invalidFiles, 'file')} need attention`}>
              <ul className="bullet-list">
                {validation.invalidEntries.slice(0, 5).map((entry) => (
                  <li key={entry.id}>
                    <span className="mono">{entry.relativePath}</span> — {entry.reason}
                  </li>
                ))}
                {validation.invalidEntries.length > 5 ? <li>and {validation.invalidEntries.length - 5} more</li> : null}
              </ul>
            </Alert>
          ) : null}

          <FilterBar>
            <SearchBar value={query} onChange={setQuery} placeholder="Search files" label="Search files" />
            <Select
              label="File type"
              value={extension}
              onChange={setExtension}
              options={[
                { value: 'all', label: 'All file types' },
                { value: '.py', label: 'Python' },
                { value: '.js', label: 'JavaScript' },
                { value: '.ts', label: 'TypeScript' },
                { value: '.md', label: 'Markdown' },
              ]}
            />
          </FilterBar>
          <div className="tree-frame">
            <RepositoryTree tree={tree} searchQuery={query} extensionFilter={extension} />
          </div>
        </section>
      ) : null}
    </>
  );
}

function RepositoryUpload() {
  const navigate = useNavigate();
  const location = useLocation();
  const notify = useToast();
  const { setSelectedRepository } = useAuth();
  // The tab lives in the URL so links to /repositories/upload and /repositories/github always land on it.
  const activeTab = location.pathname.endsWith('/upload') || location.pathname.endsWith('/add') ? 'upload' : 'github';
  const setActiveTab = (tab) => navigate(tab === 'upload' ? '/repositories/upload' : '/repositories/github', { replace: true });
  const [selectingId, setSelectingId] = useState(null);
  const [manageUrl, setManageUrl] = useState(null);
  const [repoAccess, setRepoAccess] = useState('private');

  useEffect(() => {
    authService
      .health()
      .then((health) => {
        setManageUrl(health.manage_access_url);
        setRepoAccess(health.repo_access);
      })
      .catch(() => setManageUrl(null));
  }, []);

  const selectGithubRepository = async (repo) => {
    setSelectingId(repo.id);
    try {
      setSelectedRepository(await repositoryService.getGitHubRepository(repo));
      navigate('/repositories/review');
    } catch (error) {
      notify({ tone: 'danger', title: `Could not open ${repo.fullName}`, message: error.message });
      setSelectingId(null);
    }
  };

  const reviewLocalFiles = async (normalizedFiles, tree) => {
    const repo = await repositoryService.uploadRepository(normalizedFiles);
    const topFolder = tree.children.length === 1 && tree.children[0].type === 'folder' ? tree.children[0] : null;
    setSelectedRepository({ ...repo, name: topFolder?.name || repo.name, tree: topFolder || { ...tree, name: repo.name } });
    navigate('/repositories/review');
  };

  return (
    <DashboardLayout>
      <PageHeader title="Repositories" description="Choose a repository to scan for cryptographic misuse." />

      <Tabs
        idBase={TABS_ID}
        label="Repository source"
        value={activeTab}
        onChange={setActiveTab}
        tabs={[
          { id: 'github', label: 'GitHub', icon: FolderGit2 },
          { id: 'upload', label: 'Local files', icon: Upload },
        ]}
      />

      <TabPanel idBase={TABS_ID} id={activeTab} className="tab-panel">
        {activeTab === 'github' ? (
          <GitHubRepositories onSelect={selectGithubRepository} selectingId={selectingId} manageUrl={manageUrl} repoAccess={repoAccess} />
        ) : (
          <LocalReview onReview={reviewLocalFiles} />
        )}
      </TabPanel>
    </DashboardLayout>
  );
}

export default RepositoryUpload;
