"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

import { NavBar } from "@/components/nav-bar";
import { SearchBox } from "@/components/search-box";
import { UploadForm } from "@/components/upload-form";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";

export default function AppPage() {
  const router = useRouter();
  const { authenticated, hydrated } = useAuth();

  useEffect(() => {
    if (hydrated && !authenticated) {
      router.replace("/login");
    }
  }, [hydrated, authenticated, router]);

  if (!hydrated) {
    return (
      <main className="mx-auto max-w-5xl px-4 py-16 text-center text-sm text-zinc-500">
        loading…
      </main>
    );
  }

  if (!authenticated) {
    return null;
  }

  return (
    <>
      <NavBar />
      <main className="mx-auto grid max-w-5xl gap-6 px-4 py-8 md:grid-cols-2">
        <UploadForm />
        <div className="rounded-2xl border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-900">
          <h2 className="text-base font-semibold">Search</h2>
          <p className="mt-1 mb-3 text-xs text-zinc-500">
            Full-text search across your uploaded documents.
          </p>
          <SearchBox searchFn={(q) => api.search(q)} />
        </div>
      </main>
    </>
  );
}
