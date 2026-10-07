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
  loginWithGithub: () => {
    window.location.assign(api.url('/auth/github/login'));
  },

  currentUser: async () => toUser(await api.get('/auth/me')),

  logout: async () => {
    await api.post('/auth/logout');
    return true;
  },

  health: () => api.get('/health'),
};
