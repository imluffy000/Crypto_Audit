import { api } from './api';

export const scanService = {
  startScan: (repository) =>
    api.post('/scans', { owner: repository.owner, name: repository.name, ref: repository.branch || null }),

  getScan: (scanId) => api.get(`/scans/${encodeURIComponent(scanId)}`),

  listScans: () => api.get('/scans'),

  getFindings: (scanId) => api.get(`/scans/${encodeURIComponent(scanId)}/findings`),

  getFinding: (scanId, findingId) =>
    api.get(`/scans/${encodeURIComponent(scanId)}/findings/${encodeURIComponent(findingId)}`),

  requestAiExplanation: (scanId, candidateId) =>
    api.post(`/scans/${encodeURIComponent(scanId)}/candidates/${encodeURIComponent(candidateId)}/ai-explanation`),

  reportUrl: (scanId) => api.url(`/reports/${encodeURIComponent(scanId)}.md`),
};
