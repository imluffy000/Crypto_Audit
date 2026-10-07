import { api } from './api';

function relativeTime(iso) {
  if (!iso) return 'unknown';
  const days = Math.floor((Date.now() - new Date(iso).getTime()) / 86400000);
  if (days <= 0) return 'today';
  if (days === 1) return 'yesterday';
  if (days < 30) return `${days} days ago`;
  return new Date(iso).toLocaleDateString();
}

function toTree(node) {
  return {
    name: node.name,
    type: node.type,
    size: node.size || 0,
    fileType: node.ext || '',
    children: (node.children || []).map(toTree),
  };
}

export const repositoryService = {
  // Local uploads are reviewed in the browser only; scanning requires a GitHub repository.
  uploadRepository: async (files = []) => ({
    id: `local-${Date.now()}`,
    name: 'Custom Repository',
    owner: 'local-user',
    branch: 'main',
    source: 'Local Upload',
    files: files.length,
    totalSize: files.reduce((sum, file) => sum + (file.fileSize || file.size || 0), 0),
    status: 'Review only',
    tree: { name: 'Custom Repository', type: 'folder', children: [] },
    items: files,
  }),

  getGitHubRepositories: async () => {
    const repos = await api.get('/repos');
    return repos.map((repo) => ({
      id: repo.id,
      fullName: repo.full_name,
      name: repo.name,
      owner: repo.owner,
      branch: repo.default_branch,
      description: repo.description,
      visibility: repo.private ? 'Private' : 'Public',
      language: repo.language,
      lastUpdated: relativeTime(repo.updated_at),
      updatedAt: repo.updated_at,
      size: repo.size_kb / 1024,
    }));
  },

  getGitHubRepository: async (repo) => {
    const result = await api.get(`/repos/${encodeURIComponent(repo.owner)}/${encodeURIComponent(repo.name)}/tree`);
    return {
      id: repo.id,
      name: repo.name,
      owner: repo.owner,
      fullName: result.repository,
      branch: result.ref,
      files: result.files,
      pythonFiles: result.python_files,
      totalSize: result.total_size,
      truncated: result.truncated,
      source: 'GitHub',
      status: 'Ready to scan',
      tree: toTree(result.tree),
    };
  },
};
