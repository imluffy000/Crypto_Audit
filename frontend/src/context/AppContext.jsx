import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { authService } from '../services/authService';

const AppContext = createContext(null);
const REPOSITORY_KEY = 'criptoaudit-repository';

function readStoredRepository() {
  try {
    const stored = localStorage.getItem(REPOSITORY_KEY);
    return stored ? JSON.parse(stored) : null;
  } catch {
    return null;
  }
}

export function CryptoAuditProvider({ children }) {
  // The session lives in an HttpOnly cookie; the user is always read from the server.
  const [user, setUser] = useState(null);
  const [authLoading, setAuthLoading] = useState(true);
  const [selectedRepository, setSelectedRepository] = useState(readStoredRepository);

  const refreshUser = useCallback(async () => {
    try {
      setUser(await authService.currentUser());
    } catch {
      setUser(null);
    } finally {
      setAuthLoading(false);
    }
  }, []);

  useEffect(() => {
    let active = true;
    authService
      .currentUser()
      .then((profile) => active && setUser(profile))
      .catch(() => active && setUser(null))
      .finally(() => active && setAuthLoading(false));
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    try {
      if (selectedRepository) {
        localStorage.setItem(REPOSITORY_KEY, JSON.stringify(selectedRepository));
      } else {
        localStorage.removeItem(REPOSITORY_KEY);
      }
    } catch {
      // storage unavailable (private mode): selection simply is not remembered
    }
  }, [selectedRepository]);

  const loginWithGithub = useCallback((options) => authService.loginWithGithub(options), []);

  // End this session (revoking its token), forget the selected repository, then sign in again with
  // GitHub's account picker. State is not reset first, so the page does not flash the login screen.
  const switchAccount = useCallback(async () => {
    try {
      await authService.logout();
    } catch {
      // the server also ends the old session when the new sign-in completes
    }
    try {
      localStorage.removeItem(REPOSITORY_KEY);
    } catch {
      // storage unavailable
    }
    authService.loginWithGithub({ selectAccount: true });
  }, []);

  const logout = useCallback(async () => {
    try {
      await authService.logout();
    } finally {
      setUser(null);
      setSelectedRepository(null);
    }
  }, []);

  const value = useMemo(
    () => ({ user, authLoading, refreshUser, selectedRepository, setSelectedRepository, loginWithGithub, switchAccount, logout }),
    [user, authLoading, refreshUser, selectedRepository, loginWithGithub, switchAccount, logout],
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
