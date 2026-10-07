import { Link } from 'react-router-dom';
import { ArrowLeftRight, ChevronsUpDown, FolderGit2, History, LayoutDashboard, LogOut, ShieldAlert, UserCircle2 } from 'lucide-react';
import { useAuth } from '../context/AppContext';
import BrandMark from './BrandMark';
import Dropdown from './ui/Dropdown';

// A finding's detail page (/scans/:id/findings/:fid) belongs to Findings; the rest of /scans/ to Scans & reports.
const isFindingPath = (path) => path === '/findings' || /^\/scans\/[^/]+\/findings\//.test(path);

const navItems = [
  { label: 'Dashboard', to: '/dashboard', icon: LayoutDashboard, isActive: (path) => path === '/dashboard' },
  { label: 'Repositories', to: '/repositories/github', icon: FolderGit2, isActive: (path) => /^\/repositor(y|ies)\//.test(path) },
  { label: 'Findings', to: '/findings', icon: ShieldAlert, isActive: isFindingPath },
  {
    label: 'Scans & reports',
    to: '/reports',
    icon: History,
    isActive: (path) => path === '/reports' || (path.startsWith('/scans/') && !isFindingPath(path)),
  },
];

/** Primary navigation. Rendered fixed on wide screens and inside a drawer on small ones. */
function Sidebar({ onNavigate, pathname = '' }) {
  const { user, logout, switchAccount } = useAuth();

  return (
    <div className="sidebar">
      <div className="sidebar-brand">
        <BrandMark />
        <span className="brand-name">CryptoAudit</span>
      </div>

      <nav className="sidebar-nav" aria-label="Main">
        <ul>
          {navItems.map(({ label, to, icon: Icon, isActive }) => {
            const active = isActive(pathname);
            return (
              <li key={label}>
                <Link to={to} onClick={onNavigate} className={`nav-link ${active ? 'is-active' : ''}`} aria-current={active ? 'page' : undefined}>
                  <Icon size={16} aria-hidden="true" />
                  <span>{label}</span>
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>

      <div className="sidebar-footer">
        <Dropdown
          triggerLabel={`Account menu for ${user?.login || 'user'}`}
          placement="top"
          trigger={
            <span className="account">
              {user?.avatar ? <img className="avatar" src={user.avatar} alt="" width="28" height="28" /> : <UserCircle2 size={28} aria-hidden="true" />}
              <span className="account-text">
                <span className="account-name">{user?.name || 'Signed in'}</span>
                <span className="account-login mono">{user?.login ? `@${user.login}` : ''}</span>
              </span>
              <ChevronsUpDown size={14} aria-hidden="true" className="account-chevron" />
            </span>
          }
          items={[
            { label: 'Switch account', icon: ArrowLeftRight, onSelect: switchAccount },
            { label: 'Sign out', icon: LogOut, onSelect: logout },
          ]}
        />
      </div>
    </div>
  );
}

export default Sidebar;
