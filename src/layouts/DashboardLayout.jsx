import Sidebar from '../components/Sidebar';

function DashboardLayout({ children }) {
  return (
    <div className="dashboard-shell">
      <Sidebar />
      <main className="main-panel">{children}</main>
    </div>
  );
}

export default DashboardLayout;
