import { githubRepositories, mockRepositories } from '../data/mockRepository';

const delay = (ms = 400) => new Promise((resolve) => setTimeout(resolve, ms));

export const repositoryService = {
  uploadRepository: async (files = []) => {
    await delay();

    const fileCount = files.length;
    const totalSize = files.reduce((sum, file) => sum + (file.fileSize || file.size || 0), 0);

    return {
      id: `local-${Date.now()}`,
      name: 'Custom Repository',
      owner: 'local-user',
      branch: 'main',
      source: 'Local Upload',
      files: fileCount,
      totalSize,
      status: 'Ready to scan',
      tree: { name: 'Custom Repository', type: 'folder', children: [] },
      items: files,
    };
  },

  getRepositoryTree: async (repositoryId) => {
    await delay();
    const repo = mockRepositories.find((item) => item.id === repositoryId) || mockRepositories[0];
    return repo.tree;
  },

  connectGithub: async () => {
    await delay();
    return githubRepositories;
  },

  getGitHubRepositories: async () => {
    await delay();
    return githubRepositories;
  },

  getGitHubRepositoryFiles: async (repoId) => {
    await delay();
    const repo = githubRepositories.find((item) => item.id === repoId) || githubRepositories[0];
    return repo.tree;
  },
};
