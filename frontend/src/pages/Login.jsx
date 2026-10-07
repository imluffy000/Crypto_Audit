import { useEffect, useState } from 'react';
import { Navigate, useSearchParams } from 'react-router-dom';
import { Ban, Eye, KeyRound } from 'lucide-react';
import AuthLayout from '../layouts/AuthLayout';
import BrandMark from '../components/BrandMark';
import Button from '../components/ui/Button';
import { Alert } from '../components/ui/States';
import { useAuth } from '../context/AppContext';
import { authService } from '../services/authService';

const ERROR_MESSAGES = {
  invalid_state: 'Sign-in expired or was started in another tab. Please try again.',
  authentication_error: 'GitHub did not accept the sign-in. Please try again.',
  not_configured: 'GitHub sign-in is not configured on this server.',
  server_error: 'The server hit an unexpected error while signing you in. Check the backend log and try again.',
  external_service_error: 'Could not reach GitHub to complete sign-in. Check your connection and try again.',
};

function GitHubMark() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true" fill="currentColor">
      <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z" />
    </svg>
  );
}

const ASSURANCES = [
  { icon: Eye, title: 'Read-only access', text: 'CryptoAudit reads repository contents. It never pushes, comments or opens pull requests.' },
  { icon: Ban, title: 'Code is never executed', text: 'Your repository is parsed and analysed statically. Repairs are proposed, not applied.' },
  { icon: KeyRound, title: 'Token revoked on sign-out', text: 'Your GitHub token is stored encrypted on the server, never in the browser, and is revoked when you sign out.' },
];

function Login() {
  const { user, authLoading, loginWithGithub } = useAuth();
  const [searchParams] = useSearchParams();
  const [health, setHealth] = useState(null);
  const [serverError, setServerError] = useState('');
  const [redirecting, setRedirecting] = useState(false);

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
  const signInError = errorCode ? ERROR_MESSAGES[errorCode] || `Sign-in failed (${errorCode}).` : '';
  const checking = !health && !serverError;
  const canSignIn = Boolean(health?.github_configured);

  const signIn = () => {
    setRedirecting(true);
    loginWithGithub();
  };

  return (
    <AuthLayout>
      <div className="login">
        <div className="login-brand">
          <BrandMark size={28} />
          <span className="brand-name">CryptoAudit</span>
        </div>

        <section className="login-panel" aria-labelledby="login-title">
          <h1 id="login-title">Sign in</h1>
          <p className="login-lead">
            Detect cryptographic misuse in Python repositories, review proposed repairs and see how each one was validated.
          </p>

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

          <Button variant="primary" size="lg" block onClick={signIn} disabled={!canSignIn} loading={checking || redirecting}>
            {!checking && !redirecting ? <GitHubMark /> : null}
            {checking ? 'Checking server…' : redirecting ? 'Redirecting to GitHub…' : 'Continue with GitHub'}
          </Button>

          <p className="login-scope">
            {health?.repo_access === 'public'
              ? 'Requests access to your public profile and public repositories.'
              : 'GitHub will ask for the repo scope, which is needed to read private repositories. CryptoAudit only ever sends read requests.'}
          </p>
        </section>

        <ul className="login-assurances">
          {ASSURANCES.map(({ icon: Icon, title, text }) => (
            <li key={title}>
              <Icon size={16} aria-hidden="true" />
              <div>
                <p className="assurance-title">{title}</p>
                <p className="assurance-text">{text}</p>
              </div>
            </li>
          ))}
        </ul>
      </div>
    </AuthLayout>
  );
}

export default Login;
