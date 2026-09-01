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
  signIn: () => void;
  signOut: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

const EMAIL_KEY = "nexus_email";
const ACCESS_KEY = "nexus_access_token";
const REFRESH_KEY = "nexus_refresh_token";

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [state, setState] = useState<AuthState>({
    authenticated: false,
    hydrated: false,
    email: null,
  });

  useEffect(() => {
    // Initial mount hydration: read tokens + cached email from localStorage.
    const hasTokens = !!localStorage.getItem(ACCESS_KEY);
    const email = localStorage.getItem(EMAIL_KEY);
    setState({ authenticated: hasTokens, hydrated: true, email });
  }, []);

  const setEmail = useCallback((email: string | null) => {
    if (email) localStorage.setItem(EMAIL_KEY, email);
    else localStorage.removeItem(EMAIL_KEY);
    setState((s) => ({ ...s, email }));
  }, []);

  /**
   * Mark the user as authenticated in React state.
   *
   * Why this exists: `api.setTokens(...)` only writes to localStorage. It
   * does not (and cannot, safely) update React state from inside the api
   * layer. Without this, the next render of `useAuth()` still sees
   * `authenticated: false` and protected routes bounce back to /login.
   *
   * Caller pattern after login/register:
   *     api.setTokens(tokens);  // localStorage
   *     signIn();                // React state
   *     router.push("/app");
   */
  const signIn = useCallback(() => {
    setState((s) => ({ ...s, authenticated: true }));
  }, []);

  const signOut = useCallback(() => {
    localStorage.removeItem(ACCESS_KEY);
    localStorage.removeItem(REFRESH_KEY);
    localStorage.removeItem(EMAIL_KEY);
    setState({ authenticated: false, hydrated: true, email: null });
    router.push("/login");
  }, [router]);

  const value = useMemo<AuthContextValue>(
    () => ({ ...state, setEmail, signIn, signOut }),
    [state, setEmail, signIn, signOut],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}
