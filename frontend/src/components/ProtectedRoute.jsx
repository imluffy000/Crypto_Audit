import { Navigate } from 'react-router-dom';
import { useAuth } from '../context/AppContext';

function ProtectedRoute({ children }) {
  const { user, authLoading } = useAuth();

  if (authLoading) {
    return <div className="auth-shell"><p className="subtitle">Checking your session…</p></div>;
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  return children;
}

export default ProtectedRoute;
