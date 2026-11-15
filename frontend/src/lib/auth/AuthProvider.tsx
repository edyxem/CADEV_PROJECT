"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

import { api, onAccessTokenChange, refreshSession, setAccessToken } from "@/lib/api/client";
import type { Account, AuthResponse } from "@/lib/api/types";

type Status = "loading" | "authenticated" | "anonymous";

interface AuthContextValue {
  user: Account | null;
  status: Status;
  isModerator: boolean;
  /** Photo de profil du membre connecté (URL absolue), ou null. */
  avatar: string | null;
  setAvatar: (url: string | null) => void;
  login: (identifier: string, password: string) => Promise<void>;
  register: (data: { username: string; email: string; password: string }) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<Account | null>(null);
  const [status, setStatus] = useState<Status>("loading");
  const [avatar, setAvatar] = useState<string | null>(null);
  const username = user?.username ?? null;

  // La photo vient du profil : chargée à chaque ouverture de session.
  useEffect(() => {
    if (username === null) return;
    let active = true;
    api<{ avatar: string | null }>("/profiles/me/")
      .then((profile) => {
        if (active) setAvatar(profile.avatar);
      })
      .catch(() => undefined);
    return () => {
      active = false;
    };
  }, [username]);

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
      // Après une déconnexion, l'ancienne photo n'est plus exposée.
      avatar: user ? avatar : null,
      setAvatar,
      login,
      register,
      logout,
    }),
    [user, status, avatar, login, register, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth doit être utilisé dans <AuthProvider>.");
  return context;
}
