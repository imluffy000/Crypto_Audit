const delay = (ms = 800) => new Promise((resolve) => setTimeout(resolve, ms));

export const scanService = {
  prepareScan: async (repository) => {
    await delay();
    return {
      repositoryId: repository?.id || 'unknown',
      status: 'Queued',
      message: 'Repository validated and ready for the upcoming security analysis workflow.',
    };
  },

  startScan: async (repository) => {
    await delay();
    return {
      repositoryId: repository?.id || 'unknown',
      status: 'Scan initiated',
      message: 'Security scanning functionality will be implemented in the next phase.',
    };
  },
};
