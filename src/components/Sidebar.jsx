import { NavLink } from 'react-router-dom';
import { BarChart3, FolderOpen, LogOut, ShieldCheck, Sparkles, UserCircle2 } from 'lucide-react';
import { useAuth } from '../context/AppContext';

const navItems = [
  { label: 'Dashboard', to: '/dashboard', icon: Sparkles },
  { label: 'Repositories', to: '/repositories/upload', icon: FolderOpen },
  { label: 'Reports', to: '/reports', icon: BarChart3 },
  { label: 'Settings', to: '/settings', icon: ShieldCheck },
];

function Sidebar() {
  const { user, logout } = useAuth();

  return (
    <aside className="sidebar">
      <div className="brand-block">
        <div className="brand-mark">
          <ShieldCheck size={18} />
        </div>
        <div>
          <div className="brand-name">CryptoAudit</div>
        </div>
      </div>

      <nav className="sidebar-nav" aria-label="Main navigation">
        {navItems.map(({ label, to, icon: Icon }) => (
          <NavLink key={label} to={to} className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
            <Icon size={17} />
            <span>{label}</span>
          </NavLink>
        ))}
      </nav>

      <div className="sidebar-footer">
        <div className="profile-card">
          <UserCircle2 size={18} />
          <div>
            <strong>{user?.name || 'Developer'}</strong>
            <small>{user?.email || 'developer@example.com'}</small>
          </div>
        </div>
        <button type="button" className="logout-button" onClick={logout}>
          <LogOut size={15} />
          Logout
        </button>
      </div>
    </aside>
  );
}

export default Sidebar;
