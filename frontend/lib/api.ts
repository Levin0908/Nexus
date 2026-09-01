"use client";

import type {
  DocumentPublic,
  DocumentSearchHit,
  TokenResponse,
} from "./types";

const API_BASE = (
  process.env.NEXT_PUBLIC_API_BASE ?? "http://127.0.0.1:8000"
).replace(/\/$/, "");

const ACCESS_KEY = "nexus_access_token";
const REFRESH_KEY = "nexus_refresh_token";

class ApiError extends Error {
  status: number;
  body: unknown;
  constructor(status: number, body: unknown) {
    super(typeof body === "object" && body && "detail" in body
      ? String((body as { detail: unknown }).detail)
      : `HTTP ${status}`);
    this.status = status;
    this.body = body;
  }
}

function authHeaders(token?: string | null): HeadersInit {
  const headers: Record<string, string> = {};
  if (token) headers["Authorization"] = `Bearer ${token}`;
  return headers;
}

async function handle<T>(
  res: Response,
  refreshOn401: boolean,
): Promise<T> {
  if (res.ok) {
    return res.json() as Promise<T>;
  }
  let body: unknown = null;
  try {
    body = await res.json();
  } catch {
    /* not JSON */
  }
  if (res.status === 401 && refreshOn401) {
    const refreshed = await tryRefresh();
    if (refreshed) {
      throw new RetryAfterRefresh();
    }
  }
  throw new ApiError(res.status, body);
}

/** Sentinel: thrown to signal "retry the request after refreshing the token." */
class RetryAfterRefresh extends Error {
  constructor() {
    super("retry after refresh");
  }
}

async function tryRefresh(): Promise<boolean> {
  const refresh = localStorage.getItem(REFRESH_KEY);
  if (!refresh) return false;
  const res = await fetch(`${API_BASE}/api/v1/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refresh }),
  });
  if (!res.ok) {
    localStorage.removeItem(ACCESS_KEY);
    localStorage.removeItem(REFRESH_KEY);
    return false;
  }
  const data = (await res.json()) as TokenResponse;
  localStorage.setItem(ACCESS_KEY, data.access_token);
  localStorage.setItem(REFRESH_KEY, data.refresh_token);
  return true;
}

async function request<T>(
  path: string,
  init: RequestInit = {},
  authenticated = true,
): Promise<T> {
  const doFetch = async (refreshOn401: boolean): Promise<T> => {
    const token = authenticated ? localStorage.getItem(ACCESS_KEY) : null;
    const headers = {
      ...authHeaders(token),
      ...(init.body && !(init.body instanceof FormData)
        ? { "Content-Type": "application/json" }
        : {}),
      ...(init.headers ?? {}),
    };
    const res = await fetch(`${API_BASE}${path}`, { ...init, headers });
    return handle<T>(res, refreshOn401);
  };

  try {
    return await doFetch(authenticated);
  } catch (err) {
    if (err instanceof RetryAfterRefresh && authenticated) {
      return doFetch(false);
    }
    throw err;
  }
}

export const api = {
  baseUrl: API_BASE,

  setTokens(tokens: TokenResponse): void {
    localStorage.setItem(ACCESS_KEY, tokens.access_token);
    localStorage.setItem(REFRESH_KEY, tokens.refresh_token);
  },

  clearTokens(): void {
    localStorage.removeItem(ACCESS_KEY);
    localStorage.removeItem(REFRESH_KEY);
  },

  hasTokens(): boolean {
    return (
      typeof window !== "undefined" && !!localStorage.getItem(ACCESS_KEY)
    );
  },

  async register(email: string, password: string): Promise<TokenResponse> {
    return request<TokenResponse>(
      "/api/v1/auth/register",
      {
        method: "POST",
        body: JSON.stringify({ email, password }),
      },
      false,
    );
  },

  async login(email: string, password: string): Promise<TokenResponse> {
    return request<TokenResponse>(
      "/api/v1/auth/login",
      {
        method: "POST",
        body: JSON.stringify({ email, password }),
      },
      false,
    );
  },

  async me(): Promise<{
    id: string;
    email: string;
    is_active: boolean;
    created_at: string;
  }> {
    return request("/api/v1/auth/me", { method: "GET" });
  },

  async uploadDocument(file: File): Promise<DocumentPublic> {
    const fd = new FormData();
    fd.append("file", file);
    return request<DocumentPublic>("/api/v1/documents", {
      method: "POST",
      body: fd,
    });
  },

  async getDocument(id: string): Promise<DocumentPublic> {
    return request<DocumentPublic>(`/api/v1/documents/${id}`, { method: "GET" });
  },

  async search(q: string, limit = 20): Promise<DocumentSearchHit[]> {
    const params = new URLSearchParams({ q, limit: String(limit) });
    return request<DocumentSearchHit[]>(`/api/v1/search?${params}`, {
      method: "GET",
    });
  },
};

export { ApiError };
