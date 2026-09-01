"use client";

import { useQuery } from "@tanstack/react-query";

import { api, ApiError } from "@/lib/api";
import type { DocumentPublic } from "@/lib/types";

interface Props {
  id: string;
  onClose: () => void;
}

export function DocumentDetailModal({ id, onClose }: Props) {
  const detail = useQuery<DocumentPublic, Error>({
    queryKey: ["document", id],
    queryFn: () => api.getDocument(id),
    staleTime: 60_000,
  });

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
      onClick={onClose}
    >
      <div
        className="flex max-h-[80vh] w-full max-w-2xl flex-col overflow-hidden rounded-2xl border border-zinc-200 bg-white shadow-xl dark:border-zinc-800 dark:bg-zinc-900"
        onClick={(e) => e.stopPropagation()}
      >
        <header className="flex items-center justify-between border-b border-zinc-200 px-4 py-3 dark:border-zinc-800">
          <h3 className="text-sm font-semibold">Document</h3>
          <button
            onClick={onClose}
            className="rounded-md px-2 py-1 text-sm text-zinc-500 hover:bg-zinc-100 dark:hover:bg-zinc-800"
          >
            ✕
          </button>
        </header>

        <div className="flex-1 overflow-y-auto p-4">
          {detail.isLoading && (
            <p className="text-sm text-zinc-500">loading…</p>
          )}

          {detail.isError && (
            <p className="text-sm text-red-600 dark:text-red-400">
              {detail.error instanceof ApiError
                ? detail.error.message
                : "failed to load document"}
            </p>
          )}

          {detail.data && (
            <div className="flex flex-col gap-3">
              <dl className="grid grid-cols-3 gap-2 text-xs">
                <dt className="text-zinc-500">filename</dt>
                <dd className="col-span-2 font-medium">{detail.data.filename}</dd>
                <dt className="text-zinc-500">mime</dt>
                <dd className="col-span-2">{detail.data.mime_type}</dd>
                <dt className="text-zinc-500">size</dt>
                <dd className="col-span-2">{detail.data.size_bytes} B</dd>
                <dt className="text-zinc-500">status</dt>
                <dd className="col-span-2">{detail.data.status}</dd>
              </dl>

              <div>
                <div className="mb-1 text-xs font-medium text-zinc-500">
                  extracted text
                </div>
                {detail.data.extracted_text ? (
                  <pre className="max-h-96 overflow-auto whitespace-pre-wrap rounded-md border border-zinc-200 bg-zinc-50 p-3 text-xs dark:border-zinc-800 dark:bg-zinc-950">
                    {detail.data.extracted_text}
                  </pre>
                ) : (
                  <p className="text-xs italic text-zinc-500">
                    (no extracted text available)
                  </p>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
