const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export const api = {
  baseURL: API_BASE_URL,
  get: async (url, options = {}) => {
    await new Promise((resolve) => setTimeout(resolve, 250));
    return fetch(`${API_BASE_URL}${url}`, {
      headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
      ...options,
    });
  },
  post: async (url, body, options = {}) => {
    await new Promise((resolve) => setTimeout(resolve, 350));
    return fetch(`${API_BASE_URL}${url}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
      body: JSON.stringify(body),
      ...options,
    });
  },
};
