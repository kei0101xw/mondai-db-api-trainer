import { useState, useEffect } from 'react';
import type { ReactNode } from 'react';
import { getCurrentUser, logoutUser as apiLogoutUser } from '../entities/user/api';
import { fetchCsrfToken, clearProblemCache } from '../shared/api/client';
import type { User } from '../entities/user/types';
import { AuthContext } from './auth';
import type { AuthContextType } from './auth';

interface AuthProviderProps {
  children: ReactNode;
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const initAuth = async () => {
      try {
        await fetchCsrfToken();
        const currentUser = await getCurrentUser();
        setUser(currentUser);
      } catch {
        setUser(null);
      } finally {
        setIsLoading(false);
      }
    };

    initAuth();
  }, []);

  const logout = async () => {
    try {
      await apiLogoutUser();
      setUser(null);
      // ログアウト時にSessionStorageの問題キャッシュをクリア
      clearProblemCache();
      // ログアウト後に新しいCSRFトークンを取得
      await fetchCsrfToken();
    } catch (error) {
      console.error('Logout failed:', error);
      setUser(null);
      // エラー時でもSessionStorageをクリア
      clearProblemCache();
      // エラー時でもCSRFトークンを再取得
      try {
        await fetchCsrfToken();
      } catch {
        // CSRF取得失敗は無視
      }
    }
  };

  const refreshUser = async () => {
    try {
      const previousUserId = user?.user_id;
      const currentUser = await getCurrentUser();
      // ユーザーが変わった場合（ログイン直後など）はキャッシュクリア
      if (previousUserId !== currentUser.user_id) {
        clearProblemCache();
      }
      setUser(currentUser);
    } catch {
      setUser(null);
    }
  };

  const value: AuthContextType = {
    user,
    isLoading,
    isAuthenticated: user !== null,
    setUser,
    logout,
    refreshUser,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
