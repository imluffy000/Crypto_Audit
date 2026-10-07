import { api } from './api';

// A scan that has finished never changes, and neither do its findings, so those are cached for the
// session. Scans still running are always fetched fresh so progress keeps updating.
const FOREVER = Infinity;
const isFinished = (scan) => scan?.status === 'COMPLETED' || scan?.status === 'FAILED';

export const scanService = {
  startScan: async (repository) => {
    const scan = await api.post('/scans', { owner: repository.owner, name: repository.name, ref: repository.branch || null });
    api.invalidate('/scans');
    return scan;
  },

  getScan: (scanId) => api.get(`/scans/${encodeURIComponent(scanId)}`, { ttl: FOREVER, keep: isFinished }),

  listScans: () => api.get('/scans', { ttl: 10_000 }),

  getFindings: (scanId) => api.get(`/scans/${encodeURIComponent(scanId)}/findings`, { ttl: FOREVER }),

  getFinding: (scanId, findingId) =>
    api.get(`/scans/${encodeURIComponent(scanId)}/findings/${encodeURIComponent(findingId)}`, { ttl: FOREVER }),

  requestAiExplanation: (scanId, candidateId) =>
    api.post(`/scans/${encodeURIComponent(scanId)}/candidates/${encodeURIComponent(candidateId)}/ai-explanation`),

  reportUrl: (scanId) => api.url(`/reports/${encodeURIComponent(scanId)}.md`),
};
