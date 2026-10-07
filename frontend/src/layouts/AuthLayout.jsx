import { Link } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { LoginCornerArt } from '../components/auth/LoginArtwork';

/** Signed-out page shell: one screen, with the brand palette (see brand.css and auth.css). */
function AuthLayout({ children }) {
  return (
    <div className="brand-page auth-page">
      <LoginCornerArt />
      <Link className="brand-btn brand-btn-ghost brand-btn-sm auth-back" to="/">
        <ArrowLeft size={16} className="auth-back-arrow" aria-hidden="true" />
        Back to home
      </Link>
      <main className="auth-main page-anim">{children}</main>
    </div>
  );
}

export default AuthLayout;
