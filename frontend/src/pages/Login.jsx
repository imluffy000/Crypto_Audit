import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowRight, Lock, ShieldCheck, Sparkles } from 'lucide-react';
import AuthLayout from '../layouts/AuthLayout';
import { useAuth } from '../context/AppContext';

function Login() {
  const navigate = useNavigate();
  const { loginWithGithub, loginWithEmail } = useAuth();
  const [email, setEmail] = useState('developer@example.com');
  const [password, setPassword] = useState('password123');
  const [error, setError] = useState('');

  const handleGithubLogin = async () => {
    try {
      await loginWithGithub();
      navigate('/dashboard');
    } catch (e) {
      setError('GitHub authentication failed. Please try again.');
    }
  };

  const handleEmailLogin = async (event) => {
    event.preventDefault();
    setError('');

    if (!email || !password) {
      setError('Email and password are required.');
      return;
    }

    try {
      await loginWithEmail({ email, password });
      navigate('/dashboard');
    } catch (e) {
      setError(e.message || 'Unable to sign in.');
    }
  };

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
              <p className="tagline">Secure your cryptographic code before it reaches production.</p>
            </div>
          </div>

          <h1>Welcome to CryptoAudit</h1>
          <p className="subtitle">AI-assisted cryptographic security auditing</p>

          <button type="button" className="github-button" onClick={handleGithubLogin}>
            <Sparkles size={17} /> Continue with GitHub
          </button>

          <div className="divider"><span>or</span></div>

          <form onSubmit={handleEmailLogin} className="login-form">
            <label>
              <span>Email</span>
              <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="name@company.com" />
            </label>

            <label>
              <span>Password</span>
              <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Enter your password" />
            </label>

            {error ? <div className="form-error">{error}</div> : null}

            <button type="submit" className="primary-button auth-submit">
              <Lock size={16} /> Sign In
            </button>
          </form>

          <div className="auth-links">
            <button type="button">Forgot password?</button>
            <button type="button">Create account</button>
          </div>
        </div>
      </div>
    </AuthLayout>
  );
}

export default Login;
