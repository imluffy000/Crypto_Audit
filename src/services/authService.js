import { mockUser } from '../data/mockUser';

const delay = (ms = 600) => new Promise((resolve) => setTimeout(resolve, ms));

export const authService = {
  loginWithGithub: async () => {
    await delay();
    return { ...mockUser, provider: 'github' };
  },

  loginWithEmail: async ({ email, password }) => {
    await delay();

    if (!email || !password) {
      throw new Error('Email and password are required');
    }

    return {
      ...mockUser,
      email,
      provider: 'email',
    };
  },

  logout: async () => {
    await delay(200);
    return true;
  },
};
