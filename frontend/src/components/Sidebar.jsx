import { NavLink } from 'react-router-dom';
import { ChevronsUpDown, FolderGit2, History, LayoutDashboard, LogOut, ShieldAlert, UserCircle2 } from 'lucide-react';
import { useAuth } from '../context/AppContext';
import BrandMark from './BrandMark';
import Dropdown from './ui/Dropdown';

const navItems = [
  { label: 'Dashboard', to: '/dashboard', icon: LayoutDashboard },
  { label: 'Repositories', to: '/repositories/github', icon: FolderGit2, match: ['/repositories', '/repository'] },
  { label: 'Findings', to: '/findings', icon: ShieldAlert },
  { label: 'Scans & reports', to: '/reports', icon: History, match: ['/reports', '/scans'] },
];

/** Primary navigation. Rendered fixed on wide screens and inside a drawer on small ones. */
function Sidebar({ onNavigate, pathname = '' }) {
  const { user, logout } = useAuth();

  return (
    <div className="sidebar">
      <div className="sidebar-brand">
        <BrandMark />
        <span className="brand-name">CryptoAudit</span>
      </div>

      <nav className="sidebar-nav" aria-label="Main">
        <ul>
          {navItems.map(({ label, to, icon: Icon, match }) => (
            <li key={label}>
              <NavLink
                to={to}
                onClick={onNavigate}
                className={({ isActive }) => {
                  const active = isActive || (match || []).some((prefix) => pathname.startsWith(prefix));
                  return `nav-link ${active ? 'is-active' : ''}`;
                }}
              >
                <Icon size={16} aria-hidden="true" />
                <span>{label}</span>
              </NavLink>
            </li>
          ))}
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
          items={[{ label: 'Sign out', icon: LogOut, onSelect: logout }]}
        />
      </div>
    </div>
  );
}

export default Sidebar;
