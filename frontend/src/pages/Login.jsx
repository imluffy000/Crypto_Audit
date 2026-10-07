import { useEffect, useRef, useState } from 'react';
import { Navigate, useSearchParams } from 'react-router-dom';
import { LockKeyhole } from 'lucide-react';
import AuthLayout from '../layouts/AuthLayout';
import AuthHero from '../components/auth/AuthHero';
import GithubAuthButton from '../components/auth/GithubAuthButton';
import LoginArtwork from '../components/auth/LoginArtwork';
import { Alert } from '../components/ui/States';
import { useToast } from '../components/ui/toastContext';
import { useAuth } from '../context/AppContext';
import { authService } from '../services/authService';

const ERROR_MESSAGES = {
  invalid_state: 'Sign-in expired or was started in another tab. Please try again.',
  authentication_error: 'GitHub did not accept the sign-in. Please try again.',
  not_configured: 'GitHub sign-in is not configured on this server.',
  server_error: 'The server hit an unexpected error while signing you in. Check the backend log and try again.',
  external_service_error: 'Could not reach GitHub to complete sign-in. Check your connection and try again.',
};

function Login() {
  const { user, authLoading, loginWithGithub } = useAuth();
  const [searchParams] = useSearchParams();
  const [health, setHealth] = useState(null);
  const [serverError, setServerError] = useState('');
  const [redirecting, setRedirecting] = useState(false);
  const notify = useToast();
  const announced = useRef(new Set());
  const errorCode = searchParams.get('error');

  // Each problem is announced once per page view (StrictMode runs effects twice in development).
  const announce = (key, toast) => {
    if (announced.current.has(key)) return;
    announced.current.add(key);
    notify(toast);
  };

  useEffect(() => {
    authService
      .health()
      .then((data) => {
        setHealth(data);
        if (!data.github_configured) {
          announce('not-configured', { tone: 'warning', title: 'GitHub sign-in is not configured', message: 'Add the OAuth App credentials to backend/.env and restart the server.' });
        }
      })
      .catch((error) => {
        setServerError(error.message);
        announce('server', { tone: 'danger', title: 'Server unavailable', message: error.message });
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (errorCode) {
      announce(`error-${errorCode}`, { tone: 'danger', title: 'Sign-in failed', message: ERROR_MESSAGES[errorCode] || `GitHub sign-in did not complete (${errorCode}).` });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [errorCode]);

  if (!authLoading && user) {
    return <Navigate to="/dashboard" replace />;
  }

  const signInError = errorCode ? ERROR_MESSAGES[errorCode] || `Sign-in failed (${errorCode}).` : '';
  const checking = !health && !serverError;
  const canSignIn = Boolean(health?.github_configured);

  const signIn = (selectAccount = false) => {
    setRedirecting(true);
    notify({ tone: 'info', title: 'Redirecting to GitHub', message: selectAccount ? 'Choose the account to use on the next page.' : 'Approve access on the next page.' });
    loginWithGithub({ selectAccount });
  };

  return (
    <AuthLayout>
      <div className="auth-grid">
        <AuthHero titleId="login-title">
          {signInError ? (
            <Alert tone="danger" title="Sign-in did not complete">
              {signInError}
            </Alert>
          ) : null}
          {serverError ? (
            <Alert tone="danger" title="Server unavailable">
              {serverError}
            </Alert>
          ) : null}
          {health && !health.github_configured ? (
            <Alert tone="warning" title="GitHub sign-in is not configured">
              Set <code>CRYPTOAUDIT_GITHUB_CLIENT_ID</code> and <code>CRYPTOAUDIT_GITHUB_CLIENT_SECRET</code> on the server (see{' '}
              <code>.env.example</code>).
            </Alert>
          ) : null}

          <GithubAuthButton onClick={() => signIn()} disabled={!canSignIn} loading={checking || redirecting}>
            {checking ? 'Checking server…' : redirecting ? 'Redirecting to GitHub…' : 'Continue with GitHub'}
          </GithubAuthButton>

          <p className="auth-trust">
            <LockKeyhole size={14} aria-hidden="true" />
            Read-only repository access · No code execution
          </p>

          <div className="auth-card-footer">
            <button type="button" className="link-button" onClick={() => signIn(true)} disabled={!canSignIn || redirecting}>
              Use a different GitHub account
            </button>
            <p className="auth-scope">
              {health?.repo_access === 'public'
                ? 'Requests access to your public profile and public repositories. Your token is revoked when you sign out.'
                : 'GitHub will ask for the repo scope, needed to read private repositories. CryptoAudit only sends read requests, and your token is revoked when you sign out.'}
            </p>
          </div>
        </AuthHero>

        <LoginArtwork className="auth-visual" />
      </div>
    </AuthLayout>
  );
}

export default Login;
