"use client";

import { useState } from "react";

import type { DocumentSearchHit } from "@/lib/types";
import { SearchResults } from "./search-results";

interface Props {
  searchFn: (q: string) => Promise<DocumentSearchHit[]>;
}

export function SearchBox({ searchFn }: Props) {
  const [q, setQ] = useState("");
  const [submittedQuery, setSubmittedQuery] = useState<string | null>(null);

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = q.trim();
    if (!trimmed) return;
    setSubmittedQuery(trimmed);
  };

  return (
    <div className="flex flex-col gap-3">
      <form
        onSubmit={onSubmit}
        className="flex gap-2 rounded-2xl border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-900"
      >
        <input
          type="search"
          placeholder="Search your documents…"
          minLength={1}
          maxLength={256}
          value={q}
          onChange={(e) => setQ(e.target.value)}
          className="flex-1 rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm outline-none focus:border-zinc-900 dark:border-zinc-700 dark:bg-zinc-950 dark:focus:border-zinc-200"
        />
        <button
          type="submit"
          disabled={!q.trim()}
          className="rounded-md bg-zinc-900 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-zinc-800 disabled:opacity-50 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-zinc-200"
        >
          Search
        </button>
      </form>

      <SearchResults query={submittedQuery} searchFn={searchFn} />
    </div>
  );
}
