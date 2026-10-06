import { HashRouter, Navigate, Route, Routes } from 'react-router-dom';
import './App.css';
import { CryptoAuditProvider } from './context/AppContext';
import ProtectedRoute from './components/ProtectedRoute';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import RepositoryUpload from './pages/RepositoryUpload';
import RepositoryDetails from './pages/RepositoryDetails';
import ScanPreparation from './pages/ScanPreparation';
import ScanProgress from './pages/ScanProgress';
import ComingSoon from './pages/ComingSoon';

function App() {
  return (
    <CryptoAuditProvider>
      <HashRouter>
        <Routes>
          <Route path="/" element={<Navigate to="/login" replace />} />
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
            path="/scan/preparing"
            element={
              <ProtectedRoute>
                <ScanPreparation />
              </ProtectedRoute>
            }
          />
          <Route
            path="/scan"
            element={
              <ProtectedRoute>
                <ScanProgress />
              </ProtectedRoute>
            }
          />
          <Route
            path="/findings"
            element={
              <ProtectedRoute>
                <ComingSoon title="Security Findings" subtitle="Detection engine integration will appear here." />
              </ProtectedRoute>
            }
          />
          <Route
            path="/findings/:id"
            element={
              <ProtectedRoute>
                <ComingSoon title="Finding Detail" subtitle="Finding details will appear here in the next phase." />
              </ProtectedRoute>
            }
          />
          <Route
            path="/reports"
            element={
              <ProtectedRoute>
                <ComingSoon title="Reports" subtitle="Report generation is planned for the next development phase." />
              </ProtectedRoute>
            }
          />
          <Route
            path="/reports/:id"
            element={
              <ProtectedRoute>
                <ComingSoon title="Report Detail" subtitle="Security reporting details will appear here later." />
              </ProtectedRoute>
            }
          />
          <Route
            path="/settings"
            element={
              <ProtectedRoute>
                <ComingSoon title="Settings" subtitle="System preferences will be surfaced here when the platform evolves." />
              </ProtectedRoute>
            }
          />
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </HashRouter>
    </CryptoAuditProvider>
  );
}

export default App;
