import { useAuth as useCryptoAuditAuth } from '../context/AppContext';

export function useAuth() {
  return useCryptoAuditAuth();
}
