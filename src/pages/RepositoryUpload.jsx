import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { AlertTriangle, CheckCircle2, FolderGit2, Search, ShieldCheck } from 'lucide-react';
import DashboardLayout from '../layouts/DashboardLayout';
import FileUpload from '../components/FileUpload';
import RepositoryTree from '../components/RepositoryTree';
import { normalizeFileEntry } from '../utils/fileUtils';
import { validateRepositoryFiles } from '../utils/validation';
import { repositoryService } from '../services/repositoryService';
import { useAuth } from '../context/AppContext';

const tabs = ['upload', 'github'];

function RepositoryUpload() {
  const navigate = useNavigate();
  const { setSelectedRepository } = useAuth();
  const [activeTab, setActiveTab] = useState('upload');
  const [files, setFiles] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [extensionFilter, setExtensionFilter] = useState('all');
  const [githubRepos, setGithubRepos] = useState([]);
  const [selectedGithubRepo, setSelectedGithubRepo] = useState(null);
  const [loading, setLoading] = useState(false);

  const normalizedFiles = useMemo(() => files.map((file, index) => normalizeFileEntry(file, index)), [files]);
  const validation = useMemo(() => validateRepositoryFiles(normalizedFiles), [normalizedFiles]);

  const handleLocalFiles = (incomingFiles) => {
    setFiles(incomingFiles);
  };

  const handleGithubConnect = async () => {
    setLoading(true);
    try {
      const repos = await repositoryService.getGitHubRepositories();
      setGithubRepos(repos);
      setActiveTab('github');
    } finally {
      setLoading(false);
    }
  };

  const handleSelectGithubRepo = async (repo) => {
    setLoading(true);
    setSelectedGithubRepo(repo);

    try {
      const tree = await repositoryService.getGitHubRepositoryFiles(repo.id);
      const selected = {
        id: repo.id,
        name: repo.name,
        owner: repo.owner,
        branch: repo.branch,
        files: repo.files,
        totalSize: repo.size * 1024 * 1024,
        source: 'GitHub',
        status: 'Ready to scan',
        tree,
      };

      setSelectedRepository(selected);
      navigate('/repositories/review');
    } finally {
      setLoading(false);
    }
  };

  const handleReviewLocalRepository = async () => {
    setLoading(true);
    try {
      const repo = await repositoryService.uploadRepository(normalizedFiles);
      const finalRepo = {
        ...repo,
        name: repo.name || 'Custom Repository',
        owner: 'local-user',
        branch: 'main',
        source: 'Local Upload',
        tree: {
          name: 'Custom Repository',
          type: 'folder',
          children: normalizedFiles.map((file) => ({
            name: file.relativePath.split('/').slice(1).join('/'),
            type: 'file',
            size: file.fileSize,
            fileType: file.fileType,
          })),
        },
      };
      setSelectedRepository(finalRepo);
      navigate('/repositories/review');
    } finally {
      setLoading(false);
    }
  };

  const repositoryTree = {
    name: 'repository',
    type: 'folder',
    children: normalizedFiles.reduce((acc, file) => {
      const segments = file.relativePath.split('/').filter(Boolean);
      let current = { children: acc };
      segments.forEach((segment, index) => {
        const isFile = index === segments.length - 1;
        const node = current.children.find((child) => child.name === segment);
        if (node) {
          current = node;
          return;
        }
        const created = {
          name: segment,
          type: isFile ? 'file' : 'folder',
          size: isFile ? file.fileSize : 0,
          fileType: isFile ? file.fileType : '',
          children: isFile ? [] : [],
        };
        current.children.push(created);
        current = created;
      });
      return acc;
    }, []),
  };

  return (
    <DashboardLayout>
      <div className="page-header">
        <div>
          <p className="eyebrow">Repository source</p>
          <h1>Upload Repository</h1>
        </div>
      </div>

      <div className="tab-row">
        {tabs.map((tab) => (
          <button
            key={tab}
            type="button"
            className={`tab-button ${activeTab === tab ? 'active' : ''}`}
            onClick={() => setActiveTab(tab)}
          >
            {tab === 'upload' ? 'Upload Files / Folder' : 'GitHub Repository'}
          </button>
        ))}
      </div>

      {activeTab === 'upload' ? (
        <>
          <FileUpload onFilesSelected={handleLocalFiles} />

          {normalizedFiles.length ? (
            <div className="upload-summary card-panel">
              <div className="summary-topline">
                <div>
                  <p className="eyebrow">Repository summary</p>
                  <h3>{normalizedFiles.length} files selected</h3>
                </div>
                <button type="button" className="primary-button" onClick={handleReviewLocalRepository}
                  disabled={loading}>
                  {loading ? 'Reviewing...' : 'Review Files'}
                </button>
              </div>

              <div className="metrics-row">
                <div className="metric-box">
                  <span>Total Files</span>
                  <strong>{validation.totalFiles}</strong>
                </div>
                <div className="metric-box">
                  <span>Total Size</span>
                  <strong>{(validation.totalSize / (1024 * 1024)).toFixed(1)} MB</strong>
                </div>
                <div className="metric-box success">
                  <span>Valid</span>
                  <strong>{validation.validFiles}</strong>
                </div>
                <div className="metric-box danger">
                  <span>Invalid</span>
                  <strong>{validation.invalidFiles}</strong>
                </div>
              </div>

              {validation.invalidFiles ? (
                <div className="alert-box danger">
                  <AlertTriangle size={15} />
                  <div>
                    <strong>{validation.invalidFiles} files require attention.</strong>
                    <p>Some files are too large or use unsupported extensions. You can still review the repository before starting the scan.</p>
                  </div>
                </div>
              ) : (
                <div className="alert-box success">
                  <CheckCircle2 size={15} />
                  <div>
                    <strong>All files validated.</strong>
                    <p>Repository structure is complete and ready for review.</p>
                  </div>
                </div>
              )}

              <div className="repository-toolbar">
                <div className="search-box">
                  <Search size={14} />
                  <input value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} placeholder="Search files" />
                </div>
                <select value={extensionFilter} onChange={(e) => setExtensionFilter(e.target.value)}>
                  <option value="all">All extensions</option>
                  <option value=".py">Python</option>
                  <option value=".js">JavaScript</option>
                  <option value=".ts">TypeScript</option>
                  <option value=".md">Markdown</option>
                </select>
              </div>

              <RepositoryTree tree={repositoryTree} searchQuery={searchQuery} extensionFilter={extensionFilter} />

              <div className="file-table">
                {normalizedFiles.map((file) => (
                  <div className="file-row" key={file.id}>
                    <span>{file.relativePath}</span>
                    <span>{file.fileType || 'unknown'}</span>
                    <span>{file.sizeLabel}</span>
                  </div>
                ))}
              </div>
            </div>
          ) : null}
        </>
      ) : (
        <div className="card-panel">
          <div className="summary-topline github-block">
            <div>
              <p className="eyebrow">GitHub integration</p>
              <h3>Connect GitHub Repository</h3>
            </div>
            <button type="button" className="primary-button" onClick={handleGithubConnect} disabled={loading}>
              <FolderGit2 size={15} /> {loading ? 'Loading...' : 'Connect GitHub'}
            </button>
          </div>

          {githubRepos.length ? (
            <div className="github-grid">
              {githubRepos.map((repo) => (
                <div key={repo.id} className="github-card">
                  <div className="repo-header-row">
                    <FolderGit2 size={16} />
                    <strong>{repo.name}</strong>
                  </div>
                  <p>{repo.owner}</p>
                  <div className="github-meta">
                    <span>Visibility: {repo.visibility}</span>
                    <span>Branch: {repo.branch}</span>
                    <span>Updated: {repo.lastUpdated}</span>
                  </div>
                  <button type="button" className="secondary-button" onClick={() => handleSelectGithubRepo(repo)}>
                    Select
                  </button>
                </div>
              ))}
            </div>
          ) : (
            <div className="empty-state compact">
              <div className="empty-icon">GitHub</div>
              <h3>No repositories connected yet.</h3>
              <p>Click the button above to load mock GitHub repositories for the frontend flow.</p>
            </div>
          )}
        </div>
      )}
    </DashboardLayout>
  );
}

export default RepositoryUpload;
