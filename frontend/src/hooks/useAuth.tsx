import { createContext, useContext, useState, useEffect, ReactNode, useCallback } from 'react';
import api from '../lib/api';

interface AuthUser {
  id: number;
  email?: string;
  username?: string;
  avatar_url?: string;
}

interface AuthContextType {
  user: AuthUser | null;
  loading: boolean;
  scopes: string[];
  warnings: string[];
  login: () => Promise<void>;
  logout: () => Promise<void>;
  refreshScopes: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType>(null!);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);
  const [scopes, setScopes] = useState<string[]>([]);
  const [warnings, setWarnings] = useState<string[]>([]);

  const checkAuth = useCallback(async () => {
    try {
      const res = await api.get('/auth/me');
      setUser(res.data);
    } catch {
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  const refreshScopes = useCallback(async () => {
    try {
      const res = await api.get('/auth/scopes');
      setScopes(res.data.scopes || []);
      setWarnings(res.data.warnings || []);
    } catch {
      setScopes([]);
      setWarnings([]);
    }
  }, []);

  useEffect(() => { checkAuth(); }, [checkAuth]);
  useEffect(() => { if (user) refreshScopes(); }, [user, refreshScopes]);

  const login = useCallback(async () => {
    const res = await api.post('/auth/github/login');
    window.location.href = res.data.redirect_url;
  }, []);

  const logout = useCallback(async () => {
    try { await api.delete('/auth/logout'); } catch {}
    setUser(null);
    setScopes([]);
    setWarnings([]);
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, scopes, warnings, login, logout, refreshScopes }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
