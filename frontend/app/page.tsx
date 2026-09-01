"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

import { NavBar } from "@/components/nav-bar";
import { useAuth } from "@/lib/auth";

export default function LandingPage() {
  const router = useRouter();
  const { authenticated, hydrated } = useAuth();

  useEffect(() => {
    if (hydrated && authenticated) {
      router.replace("/app");
    }
  }, [hydrated, authenticated, router]);

  return (
    <>
      <NavBar />
      <main className="mx-auto flex max-w-3xl flex-col items-center gap-6 px-4 py-16 text-center">
        <h1 className="text-4xl font-semibold tracking-tight">
          Nexus
        </h1>
        <p className="max-w-md text-lg text-zinc-600 dark:text-zinc-400">
          A personal search engine for your documents. Upload PDFs, DOCX, and
          TXT files — find them again later by keyword.
        </p>
        <div className="flex gap-3">
          <a
            href="/register"
            className="rounded-md bg-zinc-900 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-zinc-800 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-zinc-200"
          >
            Get started
          </a>
          <a
            href="/login"
            className="rounded-md border border-zinc-300 px-4 py-2 text-sm font-medium transition-colors hover:bg-zinc-100 dark:border-zinc-700 dark:hover:bg-zinc-800"
          >
            Sign in
          </a>
        </div>
      </main>
    </>
  );
}
