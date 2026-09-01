"use client";

import { useRouter } from "next/navigation";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

interface AuthState {
  authenticated: boolean;
  hydrated: boolean;
  email: string | null;
}

interface AuthContextValue extends AuthState {
  setEmail: (email: string | null) => void;
  signOut: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

const EMAIL_KEY = "nexus_email";

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [state, setState] = useState<AuthState>({
    authenticated: false,
    hydrated: false,
    email: null,
  });

  useEffect(() => {
    // Hydrate on first mount: read tokens + cached email from localStorage.
    const hasTokens =
      typeof window !== "undefined" &&
      !!localStorage.getItem("nexus_access_token");
    const email =
      typeof window !== "undefined" ? localStorage.getItem(EMAIL_KEY) : null;
    setState({ authenticated: hasTokens, hydrated: true, email });
  }, []);

  const setEmail = useCallback((email: string | null) => {
    if (typeof window !== "undefined") {
      if (email) localStorage.setItem(EMAIL_KEY, email);
      else localStorage.removeItem(EMAIL_KEY);
    }
    setState((s) => ({ ...s, email }));
  }, []);

  const signOut = useCallback(() => {
    if (typeof window !== "undefined") {
      localStorage.removeItem("nexus_access_token");
      localStorage.removeItem("nexus_refresh_token");
      localStorage.removeItem(EMAIL_KEY);
    }
    setState({ authenticated: false, hydrated: true, email: null });
    router.push("/login");
  }, [router]);

  const value = useMemo<AuthContextValue>(
    () => ({ ...state, setEmail, signOut }),
    [state, setEmail, signOut],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}
