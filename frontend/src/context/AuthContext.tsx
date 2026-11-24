import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { ACCESS_TOKEN_STORAGE_KEY, apiClient } from '../api/client';
import type { TokenResponse, UserRead } from '../types/api';

interface AuthContextValue {
  user: UserRead | null;
  isInitializing: boolean;
  setSession: (tokenResponse: TokenResponse) => void;
  refreshUser: () => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [user, setUser] = useState<UserRead | null>(null);
  const [isInitializing, setIsInitializing] = useState<boolean>(true);

  const refreshUser = useCallback(async () => {
    const token = window.localStorage.getItem(ACCESS_TOKEN_STORAGE_KEY);
    if (!token) {
      setUser(null);
      setIsInitializing(false);
      return;
    }
    try {
      const { data } = await apiClient.get<UserRead>('/auth/me');
      setUser(data);
    } catch {
      window.localStorage.removeItem(ACCESS_TOKEN_STORAGE_KEY);
      queryClient.clear();
      setUser(null);
    } finally {
      setIsInitializing(false);
    }
  }, [queryClient]);

  useEffect(() => {
    void refreshUser();
  }, [refreshUser]);

  const setSession = useCallback(
    (tokenResponse: TokenResponse) => {
      // Drop any cached queries from a previous account before activating the new session
      queryClient.clear();
      window.localStorage.setItem(ACCESS_TOKEN_STORAGE_KEY, tokenResponse.access_token);
      setUser(tokenResponse.user);
    },
    [queryClient],
  );

  const logout = useCallback(() => {
    window.localStorage.removeItem(ACCESS_TOKEN_STORAGE_KEY);
    window.sessionStorage.removeItem('learnpath_pending_display_name');
    queryClient.clear();
    setUser(null);
  }, [queryClient]);

  const value = useMemo(
    () => ({ user, isInitializing, setSession, refreshUser, logout }),
    [user, isInitializing, setSession, refreshUser, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error('useAuth must be used inside an AuthProvider.');
  }
  return ctx;
}
