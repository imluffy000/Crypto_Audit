import { HashRouter, Navigate, Route, Routes, useLocation } from 'react-router-dom';
import { CryptoAuditProvider } from './context/AppContext';
import ProtectedRoute from './components/ProtectedRoute';
import ToastProvider from './components/ui/ToastProvider';
import { usePageTransition } from './hooks/usePageTransition';
import Home from './pages/Home';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import RepositoryUpload from './pages/RepositoryUpload';
import RepositoryDetails from './pages/RepositoryDetails';
import ScanResults from './pages/ScanResults';
import FindingDetail from './pages/FindingDetail';
import Reports from './pages/Reports';
import Findings from './pages/Findings';

/** All routes. Each page appears immediately with a short fade-in (see usePageTransition). */
function AppRoutes() {
  const location = useLocation();
  const pageKey = usePageTransition(location);

  return (
    <div key={pageKey} className="route-stage">
      <Routes location={location}>
        <Route path="/" element={<Home />} />
        <Route path="/login" element={<Login />} />

        <Route
          path="/dashboard"
          element={
            <ProtectedRoute>
              <Dashboard />
            </ProtectedRoute>
          }
        />
        <Route
          path="/repository/add"
          element={
            <ProtectedRoute>
              <RepositoryUpload />
            </ProtectedRoute>
          }
        />
        <Route
          path="/repositories/upload"
          element={
            <ProtectedRoute>
              <RepositoryUpload />
            </ProtectedRoute>
          }
        />
        <Route
          path="/repositories/github"
          element={
            <ProtectedRoute>
              <RepositoryUpload />
            </ProtectedRoute>
          }
        />
        <Route
          path="/repositories/review"
          element={
            <ProtectedRoute>
              <RepositoryDetails />
            </ProtectedRoute>
          }
        />
        <Route
          path="/scans/:scanId"
          element={
            <ProtectedRoute>
              <ScanResults />
            </ProtectedRoute>
          }
        />
        <Route
          path="/scans/:scanId/findings/:findingId"
          element={
            <ProtectedRoute>
              <FindingDetail />
            </ProtectedRoute>
          }
        />
        <Route
          path="/findings"
          element={
            <ProtectedRoute>
              <Findings />
            </ProtectedRoute>
          }
        />
        <Route
          path="/reports"
          element={
            <ProtectedRoute>
              <Reports />
            </ProtectedRoute>
          }
        />
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </div>
  );
}

function App() {
  return (
    <ToastProvider>
      <CryptoAuditProvider>
        <HashRouter>
          <AppRoutes />
        </HashRouter>
      </CryptoAuditProvider>
    </ToastProvider>
  );
}

export default App;
