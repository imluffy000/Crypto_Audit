// CryptoAudit API client. In development Vite proxies /api to the backend (see vite.config.js).
const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '');

export class ApiError extends Error {
  constructor(status, code, message) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

async function request(path, { method = 'GET', body } = {}) {
  let response;
  try {
    response = await fetch(`${API_BASE_URL}/api${path}`, {
      method,
      credentials: 'include',
      headers: body ? { 'Content-Type': 'application/json' } : undefined,
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new ApiError(0, 'NETWORK_ERROR', 'Cannot reach the CryptoAudit server. Is `cryptoaudit serve` running?');
  }
  if (response.status === 204) return null;
  const data = await response.json().catch(() => null);
  if (!response.ok) {
    throw new ApiError(
      response.status,
      data?.error?.code || `HTTP_${response.status}`,
      data?.error?.message || response.statusText || 'Request failed',
    );
  }
  return data;
}

/*
 * In-memory response cache, so revisiting a page or stepping between findings answers immediately.
 * It lives only for this browser tab and is cleared on sign-out and account switch, so one account's
 * data is never shown to another.
 *   ttl: milliseconds a response stays fresh (Infinity for data that cannot change, e.g. a finished scan)
 *   keep(data): whether this particular response may be cached at all (e.g. not a scan still running)
 * Identical requests already in flight share one network call.
 */
const cache = new Map();
const inflight = new Map();

function cachedGet(path, { ttl = 0, keep = () => true } = {}) {
  const hit = cache.get(path);
  if (hit && Date.now() - hit.at < ttl) return Promise.resolve(hit.data);
  if (inflight.has(path)) return inflight.get(path);
  const pending = request(path)
    .then((data) => {
      if (ttl > 0 && keep(data)) cache.set(path, { data, at: Date.now() });
      return data;
    })
    .finally(() => inflight.delete(path));
  inflight.set(path, pending);
  return pending;
}

export const api = {
  get: (path, options) => cachedGet(path, options),
  post: (path, body) => request(path, { method: 'POST', body }),
  url: (path) => `${API_BASE_URL}/api${path}`,
  /** Forget cached responses: all of them, or those whose path starts with `prefix`. */
  invalidate: (prefix = '') => {
    [...cache.keys()].filter((key) => key.startsWith(prefix)).forEach((key) => cache.delete(key));
  },
};
