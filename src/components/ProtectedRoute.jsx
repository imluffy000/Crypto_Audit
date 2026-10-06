import { Navigate } from 'react-router-dom';
import { useAuth } from '../context/AppContext';

function ProtectedRoute({ children }) {
  const { user } = useAuth();

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  return children;
}

export default ProtectedRoute;
