import { api } from './api';

function toUser(profile) {
  return {
    id: profile.id,
    login: profile.login,
    name: profile.name || profile.login,
    email: profile.email || `@${profile.login}`,
    avatar: profile.avatar_url,
    provider: 'github',
  };
}

export const authService = {
  // Full-page redirect: GitHub sign-in is handled by the backend, which sets an HttpOnly session cookie.
  // selectAccount asks GitHub to show its account picker instead of reusing the account signed in to github.com.
  loginWithGithub: ({ selectAccount = false } = {}) => {
    window.location.assign(api.url(`/auth/github/login${selectAccount ? '?select_account=true' : ''}`));
  },

  currentUser: async () => toUser(await api.get('/auth/me')),

  // Whatever happens, forget cached data: the next person to sign in must not see this account's scans.
  logout: async () => {
    try {
      await api.post('/auth/logout');
    } finally {
      api.invalidate();
    }
    return true;
  },

  health: () => api.get('/health', { ttl: 30_000 }),
};
