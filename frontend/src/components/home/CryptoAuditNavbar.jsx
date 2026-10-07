import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import CryptoAuditLogo from '../brand/CryptoAuditLogo';

/**
 * Fixed, lightweight top bar for the home page. It stays transparent over the hero and only gains
 * a background once the page has scrolled, so text below it stays readable.
 * `links` are [{ label, index }] slide targets; `onNavigate(index)` scrolls to a slide.
 */
function CryptoAuditNavbar({ links, active, onNavigate, signInTo, signInLabel, analyzeTo }) {
  const [raised, setRaised] = useState(false);

  useEffect(() => {
    const update = () => setRaised(window.scrollY > 8);
    update();
    window.addEventListener('scroll', update, { passive: true });
    return () => window.removeEventListener('scroll', update);
  }, []);

  return (
    <header className={`home-nav ${raised ? 'is-raised' : ''}`}>
      <div className="home-nav-inner">
        <Link
          to="/"
          className="home-nav-brand"
          aria-label="CryptoAudit, back to top"
          onClick={(event) => {
            event.preventDefault();
            onNavigate(0);
          }}
        >
          <CryptoAuditLogo size={30} />
        </Link>

        <nav className="home-nav-links" aria-label="Page sections">
          <ul>
            {links.map((link) => (
              <li key={link.label}>
                <button
                  type="button"
                  className={`home-nav-link ${active === link.index ? 'is-active' : ''}`}
                  aria-current={active === link.index ? 'true' : undefined}
                  onClick={() => onNavigate(link.index)}
                >
                  {link.label}
                </button>
              </li>
            ))}
          </ul>
        </nav>

        <div className="home-nav-actions">
          <Link className="brand-btn brand-btn-ghost brand-btn-sm home-nav-signin" to={signInTo}>
            {signInLabel}
          </Link>
          <Link className="brand-btn brand-btn-primary brand-btn-sm" to={analyzeTo}>
            Analyze Repository
          </Link>
        </div>
      </div>
    </header>
  );
}

export default CryptoAuditNavbar;
