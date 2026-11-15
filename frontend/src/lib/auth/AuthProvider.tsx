"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

import { api, onAccessTokenChange, refreshSession, setAccessToken } from "@/lib/api/client";
import type { Account, AuthResponse } from "@/lib/api/types";

type Status = "loading" | "authenticated" | "anonymous";

interface AuthContextValue {
  user: Account | null;
  status: Status;
  isModerator: boolean;
  login: (identifier: string, password: string) => Promise<void>;
  register: (data: { username: string; email: string; password: string }) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<Account | null>(null);
  const [status, setStatus] = useState<Status>("loading");

  // Au chargement : la session est restaurée à partir du cookie de rafraîchissement.
  useEffect(() => {
    let active = true;
    refreshSession()
      .then(async (ok) => {
        if (!ok) return null;
        return api<Account>("/auth/me/");
      })
      .then((account) => {
        if (!active) return;
        setUser(account ?? null);
        setStatus(account ? "authenticated" : "anonymous");
      })
      .catch(() => active && setStatus("anonymous"));
    const unsubscribe = onAccessTokenChange((token) => {
      if (token === null) {
        setUser(null);
        setStatus("anonymous");
      }
    });
    return () => {
      active = false;
      unsubscribe();
    };
  }, []);

  const openSession = useCallback((response: AuthResponse) => {
    setAccessToken(response.access);
    setUser(response.user);
    setStatus("authenticated");
  }, []);

  const login = useCallback(
    async (identifier: string, password: string) => {
      openSession(
        await api<AuthResponse>("/auth/login/", {
          method: "POST",
          body: { identifier, password },
          withCredentials: true,
        }),
      );
    },
    [openSession],
  );

  const register = useCallback(
    async (data: { username: string; email: string; password: string }) => {
      openSession(
        await api<AuthResponse>("/auth/register/", { method: "POST", body: data, withCredentials: true }),
      );
    },
    [openSession],
  );

  const logout = useCallback(async () => {
    try {
      await api("/auth/logout/", { method: "POST", withCredentials: true });
    } finally {
      setAccessToken(null);
    }
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      status,
      isModerator: user?.role === "MODERATOR" || user?.role === "ADMIN",
      login,
      register,
      logout,
    }),
    [user, status, login, register, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth doit être utilisé dans <AuthProvider>.");
  return context;
}
