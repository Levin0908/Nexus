"use client";

import { useAuth } from "@/lib/auth";

export function NavBar() {
  const { authenticated, hydrated, email, signOut } = useAuth();

  return (
    <header className="border-b border-zinc-200 bg-white dark:border-zinc-800 dark:bg-zinc-900">
      <div className="mx-auto flex h-14 max-w-5xl items-center justify-between px-4">
        <a
          href={authenticated ? "/app" : "/"}
          className="text-lg font-semibold tracking-tight"
        >
          Nexus
        </a>

        {hydrated && authenticated ? (
          <div className="flex items-center gap-4 text-sm">
            <span className="text-zinc-500">{email}</span>
            <button
              onClick={signOut}
              className="rounded-md border border-zinc-300 px-3 py-1 text-sm transition-colors hover:bg-zinc-100 dark:border-zinc-700 dark:hover:bg-zinc-800"
            >
              Sign out
            </button>
          </div>
        ) : (
          <nav className="flex items-center gap-3 text-sm">
            <a className="underline" href="/login">
              Sign in
            </a>
            <a
              className="rounded-md bg-zinc-900 px-3 py-1 text-white dark:bg-zinc-100 dark:text-zinc-900"
              href="/register"
            >
              Create account
            </a>
          </nav>
        )}
      </div>
    </header>
  );
}
