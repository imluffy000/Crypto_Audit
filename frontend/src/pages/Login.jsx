import { useEffect, useState } from 'react';
import { Navigate, useSearchParams } from 'react-router-dom';
import { AlertTriangle, ShieldCheck } from 'lucide-react';
import AuthLayout from '../layouts/AuthLayout';
import { useAuth } from '../context/AppContext';
import { authService } from '../services/authService';

const ERROR_MESSAGES = {
  invalid_state: 'Sign-in expired or was started in another tab. Please try again.',
  authentication_error: 'GitHub did not accept the sign-in. Please try again.',
  not_configured: 'GitHub sign-in is not configured on this server.',
};

function GitHubMark() {
  return (
    <svg width="17" height="17" viewBox="0 0 16 16" aria-hidden="true" fill="currentColor">
      <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z" />
    </svg>
  );
}

function Login() {
  const { user, authLoading, loginWithGithub } = useAuth();
  const [searchParams] = useSearchParams();
  const [health, setHealth] = useState(null);
  const [serverError, setServerError] = useState('');

  useEffect(() => {
    authService
      .health()
      .then(setHealth)
      .catch((error) => setServerError(error.message));
  }, []);

  if (!authLoading && user) {
    return <Navigate to="/dashboard" replace />;
  }

  const errorCode = searchParams.get('error');
  const error = serverError || (errorCode ? ERROR_MESSAGES[errorCode] || `Sign-in failed (${errorCode}).` : '');
  const canSignIn = health?.github_configured;

  return (
    <AuthLayout>
      <div className="login-page">
        <div className="auth-card login-card">
          <div className="brand-header">
            <div className="brand-mark large">
              <ShieldCheck size={24} />
            </div>
            <div>
              <div className="brand-name">CryptoAudit</div>
              <p className="tagline">Find, repair and independently validate cryptographic misuse in Python.</p>
            </div>
          </div>

          <h1>Welcome to CryptoAudit</h1>
          <p className="subtitle">Sign in with GitHub, choose a repository, and get validated repair suggestions.</p>

          <button type="button" className="github-button" onClick={loginWithGithub} disabled={!canSignIn}>
            <GitHubMark /> Continue with GitHub
          </button>

          {health && !health.github_configured ? (
            <div className="alert-box warning">
              <AlertTriangle size={15} />
              <div>
                <strong>GitHub sign-in not configured.</strong>
                <p>Set CRYPTOAUDIT_GITHUB_CLIENT_ID and CRYPTOAUDIT_GITHUB_CLIENT_SECRET on the server (see .env.example).</p>
              </div>
            </div>
          ) : null}

          {error ? <div className="form-error">{error}</div> : null}

          <p className="fine-print">
            CryptoAudit only reads your repositories; it never pushes or changes anything on GitHub. Your code is analysed and repaired but never executed, and signing out revokes CryptoAudit's access token.
          </p>
        </div>
      </div>
    </AuthLayout>
  );
}

export default Login;
