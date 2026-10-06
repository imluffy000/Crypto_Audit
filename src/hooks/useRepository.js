import { useAuth } from '../context/AppContext';

export function useRepository() {
  const { selectedRepository, setSelectedRepository } = useAuth();
  return { selectedRepository, setSelectedRepository };
}
