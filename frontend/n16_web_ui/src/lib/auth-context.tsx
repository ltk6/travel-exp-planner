"use client";

import { createContext, useContext, useState, useEffect, type ReactNode } from "react";

type AuthUser = { userId: number; username: string; token?: string } | null;

type AuthContextValue = {
  user: AuthUser;
  login: (userId: number, username: string, token?: string) => void;
  logout: () => void;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser>(null);

  useEffect(() => {
    try {
      const stored = sessionStorage.getItem("auth_user");
      if (stored) {
        const parsed = JSON.parse(stored);
        setTimeout(() => {
          setUser(parsed);
        }, 0);
      }
    } catch {
      sessionStorage.removeItem("auth_user");
    }

    async function checkServerReset() {
      try {
        const res = await fetch("/api/health");
        if (!res.ok) return;
        const data = await res.json();
        if (data.server_boot_id) {
          const storedBootId = sessionStorage.getItem("server_boot_id");
          if (storedBootId && storedBootId !== data.server_boot_id) {
            console.warn("Server reset detected! Logging out...");
            setUser(null);
            sessionStorage.removeItem("auth_user");
          }
          sessionStorage.setItem("server_boot_id", data.server_boot_id);
        }
      } catch (err) {
        console.error("Failed to check server health:", err);
      }
    }

    checkServerReset();
  }, []);

  function login(userId: number, username: string, token?: string) {
    const u = { userId, username, token };
    setUser(u);
    sessionStorage.setItem("auth_user", JSON.stringify(u));
  }

  function logout() {
    setUser(null);
    sessionStorage.removeItem("auth_user");
  }

  return <AuthContext.Provider value={{ user, login, logout }}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
