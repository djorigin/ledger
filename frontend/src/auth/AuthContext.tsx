import { createContext, useCallback, useContext, useEffect, useState } from "react";
import type { ReactNode } from "react";

import { fetchMe, login as apiLogin } from "@/api/auth";
import { performRefresh, setAccessToken, setSessionExpiredHandler } from "@/api/client";
import { clearStoredRefreshToken, getStoredRefreshToken, setStoredRefreshToken } from "@/auth/tokenStorage";
import type { MeResponse } from "@/types/api";

type AuthStatus = "loading" | "authenticated" | "unauthenticated";

interface AuthContextValue {
  user: MeResponse | null;
  status: AuthStatus;
  login(email: string, password: string): Promise<void>;
  logout(): void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<MeResponse | null>(null);
  const [status, setStatus] = useState<AuthStatus>("loading");

  const logout = useCallback(() => {
    setAccessToken(null);
    clearStoredRefreshToken();
    setUser(null);
    setStatus("unauthenticated");
  }, []);

  useEffect(() => {
    setSessionExpiredHandler(logout);
    return () => setSessionExpiredHandler(null);
  }, [logout]);

  useEffect(() => {
    async function silentlyRestoreSession() {
      const refreshToken = getStoredRefreshToken();
      if (!refreshToken) {
        setStatus("unauthenticated");
        return;
      }
      try {
        await performRefresh();
        const me = await fetchMe();
        setUser(me);
        setStatus("authenticated");
      } catch {
        clearStoredRefreshToken();
        setStatus("unauthenticated");
      }
    }
    void silentlyRestoreSession();
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const tokens = await apiLogin(email, password);
    setStoredRefreshToken(tokens.refresh);
    setAccessToken(tokens.access);
    const me = await fetchMe();
    setUser(me);
    setStatus("authenticated");
  }, []);

  return (
    <AuthContext.Provider value={{ user, status, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider.");
  }
  return context;
}
