"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { api, ApiError } from "@/lib/api";
import type { DocumentSearchHit } from "@/lib/types";
import { DocumentDetailModal } from "./document-detail-modal";

interface Props {
  query: string | null;
  searchFn: (q: string) => Promise<DocumentSearchHit[]>;
}

export function SearchResults({ query, searchFn }: Props) {
  const [openId, setOpenId] = useState<string | null>(null);

  const search = useQuery<DocumentSearchHit[], Error>({
    queryKey: ["search", query],
    queryFn: () => (query ? searchFn(query) : Promise.resolve([])),
    enabled: !!query,
    staleTime: 30_000,
  });

  if (!query) {
    return (
      <div className="rounded-2xl border border-dashed border-zinc-300 bg-white p-6 text-center text-sm text-zinc-500 dark:border-zinc-700 dark:bg-zinc-900">
        Type something and hit Search.
      </div>
    );
  }

  if (search.isLoading) {
    return (
      <div className="rounded-2xl border border-zinc-200 bg-white p-6 text-center text-sm text-zinc-500 dark:border-zinc-800 dark:bg-zinc-900">
        Searching…
      </div>
    );
  }

  if (search.isError) {
    return (
      <div className="rounded-2xl border border-red-200 bg-red-50 p-4 text-sm text-red-700 dark:border-red-900 dark:bg-red-950 dark:text-red-300">
        {search.error instanceof ApiError
          ? search.error.message
          : "search failed"}
      </div>
    );
  }

  const hits = search.data ?? [];

  if (hits.length === 0) {
    return (
      <div className="rounded-2xl border border-zinc-200 bg-white p-6 text-center text-sm text-zinc-500 dark:border-zinc-800 dark:bg-zinc-900">
        No matches for <strong>{query}</strong>.
      </div>
    );
  }

  return (
    <>
      <ul className="flex flex-col gap-2">
        {hits.map((hit) => (
          <li
            key={hit.id}
            className="rounded-xl border border-zinc-200 bg-white p-3 transition-colors hover:border-zinc-400 dark:border-zinc-800 dark:bg-zinc-900 dark:hover:border-zinc-600"
          >
            <button
              onClick={() => setOpenId(hit.id)}
              className="flex w-full items-center justify-between gap-4 text-left"
            >
              <div>
                <div className="text-sm font-medium">{hit.filename}</div>
                <div className="text-xs text-zinc-500">
                  {hit.mime_type} · {(hit.size_bytes / 1024).toFixed(1)} KiB ·{" "}
                  {hit.status}
                </div>
              </div>
              <div className="text-xs text-zinc-500">
                rank {hit.rank.toFixed(3)}
              </div>
            </button>
          </li>
        ))}
      </ul>

      {openId && (
        <DocumentDetailModal
          id={openId}
          onClose={() => setOpenId(null)}
        />
      )}
    </>
  );
}
