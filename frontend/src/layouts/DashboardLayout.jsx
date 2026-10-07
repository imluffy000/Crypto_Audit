import { useCallback, useState } from 'react';
import { useLocation } from 'react-router-dom';
import { Menu } from 'lucide-react';
import Sidebar from '../components/Sidebar';
import BrandMark from '../components/BrandMark';
import Drawer from '../components/ui/Drawer';

/** Signed-in shell: fixed sidebar on wide screens; top bar + navigation drawer below 1024px. */
function DashboardLayout({ children, width = 'default' }) {
  const { pathname } = useLocation();
  const [navOpen, setNavOpen] = useState(false);
  const closeNav = useCallback(() => setNavOpen(false), []);

  return (
    <div className="app-shell">
      <a className="skip-link" href="#main-content" onClick={(event) => {
        event.preventDefault();
        document.getElementById('main-content')?.focus();
      }}>
        Skip to content
      </a>

      <aside className="app-sidebar">
        <Sidebar pathname={pathname} />
      </aside>

      <header className="app-topbar">
        <button type="button" className="btn btn-ghost btn-md btn-icon" onClick={() => setNavOpen(true)} aria-label="Open navigation" aria-expanded={navOpen}>
          <Menu size={18} aria-hidden="true" />
        </button>
        <span className="topbar-brand">
          <BrandMark size={20} />
          CryptoAudit
        </span>
      </header>

      <Drawer open={navOpen} onClose={closeNav} label="Navigation">
        <Sidebar pathname={pathname} onNavigate={closeNav} />
      </Drawer>

      <main id="main-content" className={`app-main width-${width}`} tabIndex={-1}>
        <div className="app-content page-anim">{children}</div>
      </main>
    </div>
  );
}

export default DashboardLayout;
