"use client";

import { createContext, useContext, useState, useEffect, type ReactNode } from "react";

type AuthUser = { userId: number; username: string } | null;

type AuthContextValue = {
  user: AuthUser;
  login: (userId: number, username: string) => void;
  logout: () => void;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState(() => {
    try {
      const stored = localStorage.getItem("auth_user");
      return stored ? JSON.parse(stored) : null;
    } catch {
      localStorage.removeItem("auth_user");
      return null;
    }
  });

  function login(userId: number, username: string) {
    const u = { userId, username };
    setUser(u);
    localStorage.setItem("auth_user", JSON.stringify(u));
  }

  function logout() {
    setUser(null);
    localStorage.removeItem("auth_user");
  }

  return <AuthContext.Provider value={{ user, login, logout }}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
