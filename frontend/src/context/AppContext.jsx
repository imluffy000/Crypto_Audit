import { createContext, useContext, useEffect, useMemo, useState } from 'react';
import { authService } from '../services/authService';
import { mockUser } from '../data/mockUser';

const AppContext = createContext(null);
const STORAGE_KEYS = {
  user: 'criptoaudit-user',
  repository: 'criptoaudit-repository',
};

export function CryptoAuditProvider({ children }) {
  const [user, setUser] = useState(() => {
    const storedUser = localStorage.getItem(STORAGE_KEYS.user);
    return storedUser ? JSON.parse(storedUser) : null;
  });

  const [selectedRepository, setSelectedRepository] = useState(() => {
    const storedRepository = localStorage.getItem(STORAGE_KEYS.repository);
    return storedRepository ? JSON.parse(storedRepository) : null;
  });

  useEffect(() => {
    if (user) {
      localStorage.setItem(STORAGE_KEYS.user, JSON.stringify(user));
    } else {
      localStorage.removeItem(STORAGE_KEYS.user);
    }
  }, [user]);

  useEffect(() => {
    if (selectedRepository) {
      localStorage.setItem(STORAGE_KEYS.repository, JSON.stringify(selectedRepository));
    } else {
      localStorage.removeItem(STORAGE_KEYS.repository);
    }
  }, [selectedRepository]);

  const loginWithGithub = async () => {
    const response = await authService.loginWithGithub();
    setUser(response);
    return response;
  };

  const loginWithEmail = async ({ email, password }) => {
    const response = await authService.loginWithEmail({ email, password });
    setUser(response);
    return response;
  };

  const logout = async () => {
    await authService.logout();
    setUser(null);
    setSelectedRepository(null);
  };

  const value = useMemo(
    () => ({
      user,
      setUser,
      selectedRepository,
      setSelectedRepository,
      loginWithGithub,
      loginWithEmail,
      logout,
      mockUser,
    }),
    [user, selectedRepository],
  );

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}

export function useAuth() {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error('useAuth must be used within a CryptoAuditProvider');
  }
  return context;
}
