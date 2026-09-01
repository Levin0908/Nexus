"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";

interface Props {
  mode: "login" | "register";
}

export function AuthForm({ mode }: Props) {
  const router = useRouter();
  const { setEmail, signIn } = useAuth();
  const [email, setEmailInput] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const tokens =
        mode === "login"
          ? await api.login(email, password)
          : await api.register(email, password);
      api.setTokens(tokens);
      setEmail(email);
      // Tell React we're now authenticated, otherwise /app's effect
      // (which reads `useAuth().authenticated`) will bounce us back to /login.
      signIn();
      router.push("/app");
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError("network error");
      }
    } finally {
      setSubmitting(false);
    }
  };

  const isLogin = mode === "login";

  return (
    <form
      onSubmit={onSubmit}
      className="mx-auto flex w-full max-w-sm flex-col gap-4 rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm dark:border-zinc-800 dark:bg-zinc-900"
    >
      <h1 className="text-xl font-semibold">
        {isLogin ? "Sign in to Nexus" : "Create an account"}
      </h1>

      <label className="flex flex-col gap-1 text-sm">
        <span className="font-medium">Email</span>
        <input
          type="email"
          required
          autoComplete="email"
          value={email}
          onChange={(e) => setEmailInput(e.target.value)}
          className="rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm outline-none focus:border-zinc-900 dark:border-zinc-700 dark:bg-zinc-950 dark:focus:border-zinc-200"
        />
      </label>

      <label className="flex flex-col gap-1 text-sm">
        <span className="font-medium">Password</span>
        <input
          type="password"
          required
          minLength={8}
          maxLength={128}
          autoComplete={isLogin ? "current-password" : "new-password"}
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm outline-none focus:border-zinc-900 dark:border-zinc-700 dark:bg-zinc-950 dark:focus:border-zinc-200"
        />
        <span className="text-xs text-zinc-500">
          {isLogin ? "" : "At least 8 characters."}
        </span>
      </label>

      {error && (
        <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-950 dark:text-red-300">
          {error}
        </p>
      )}

      <button
        type="submit"
        disabled={submitting}
        className="rounded-md bg-zinc-900 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-zinc-800 disabled:opacity-50 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-zinc-200"
      >
        {submitting
          ? isLogin
            ? "Signing in…"
            : "Creating account…"
          : isLogin
            ? "Sign in"
            : "Create account"}
      </button>

      <p className="text-center text-xs text-zinc-500">
        {isLogin ? (
          <>
            New here?{" "}
            <a className="underline" href="/register">
              Create an account
            </a>
          </>
        ) : (
          <>
            Already have one?{" "}
            <a className="underline" href="/login">
              Sign in
            </a>
          </>
        )}
      </p>
    </form>
  );
}
