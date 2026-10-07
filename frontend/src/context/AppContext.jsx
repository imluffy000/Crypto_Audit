import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { authService } from '../services/authService';
import { useToast } from '../components/ui/toastContext';

const AppContext = createContext(null);
const REPOSITORY_KEY = 'criptoaudit-repository';
// Set just before the GitHub redirect so the app can confirm a completed sign-in when it comes back.
const SIGNING_IN_KEY = 'cryptoaudit-signing-in';

function markSigningIn(on) {
  try {
    if (on) sessionStorage.setItem(SIGNING_IN_KEY, '1');
    else sessionStorage.removeItem(SIGNING_IN_KEY);
  } catch {
    // storage unavailable: the sign-in confirmation is simply not shown
  }
}

function wasSigningIn() {
  try {
    return sessionStorage.getItem(SIGNING_IN_KEY) === '1';
  } catch {
    return false;
  }
}

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
  const notify = useToast();
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
      .then((profile) => {
        if (!active) return;
        setUser(profile);
        if (wasSigningIn()) {
          notify({ tone: 'success', title: 'Signed in', message: `Welcome, @${profile.login}.` });
        }
      })
      .catch(() => active && setUser(null))
      .finally(() => {
        if (!active) return;
        markSigningIn(false); // a failed sign-in is reported by the login page
        setAuthLoading(false);
      });
    return () => {
      active = false;
    };
  }, [notify]);

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

  const loginWithGithub = useCallback((options) => {
    markSigningIn(true);
    authService.loginWithGithub(options);
  }, []);

  // End this session (revoking its token), forget the selected repository, then sign in again with
  // GitHub's account picker. State is not reset first, so the page does not flash the login screen.
  const switchAccount = useCallback(async () => {
    notify({ tone: 'info', title: 'Switching account', message: "Signing out and opening GitHub's account picker…" });
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
    markSigningIn(true);
    authService.loginWithGithub({ selectAccount: true });
  }, [notify]);

  const logout = useCallback(async () => {
    try {
      await authService.logout();
      notify({ tone: 'success', title: 'Signed out', message: 'Your GitHub access token was revoked.' });
    } catch {
      notify({
        tone: 'warning',
        title: 'Signed out on this device',
        message: 'The server could not be reached to revoke the token. You can revoke it in GitHub settings.',
      });
    } finally {
      setUser(null);
      setSelectedRepository(null);
    }
  }, [notify]);

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
