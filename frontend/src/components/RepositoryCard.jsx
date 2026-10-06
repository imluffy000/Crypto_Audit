import { ArrowRight, FolderGit2, GitBranch, ShieldCheck } from 'lucide-react';
import { formatFileSize } from '../utils/fileUtils';

function RepositoryCard({ repository, onView }) {
  return (
    <article className="repository-card">
      <div className="repo-card-header">
        <div className="repo-icon">
          <FolderGit2 size={16} />
        </div>
        <div>
          <h3>{repository.name}</h3>
          <p>{repository.owner}</p>
        </div>
      </div>

      <div className="meta-grid">
        <div>
          <span className="meta-label">Branch</span>
          <div className="meta-value"><GitBranch size={14} /> {repository.branch}</div>
        </div>
        <div>
          <span className="meta-label">Files</span>
          <div className="meta-value">{repository.files || repository.fileCount || 0} files</div>
        </div>
        <div>
          <span className="meta-label">Size</span>
          <div className="meta-value">{formatFileSize(repository.totalSize || repository.size * 1024 * 1024 || 0)}</div>
        </div>
      </div>

      <div className="repo-status-row">
        <span className="status-pill success"><ShieldCheck size={12} /> Ready to scan</span>
        <button type="button" className="secondary-button" onClick={() => onView(repository)}>
          View Repository <ArrowRight size={15} />
        </button>
      </div>
    </article>
  );
}

export default RepositoryCard;
