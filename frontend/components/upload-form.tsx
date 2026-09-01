"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRef, useState } from "react";

import { api, ApiError } from "@/lib/api";
import type { DocumentPublic } from "@/lib/types";

export function UploadForm() {
  const inputRef = useRef<HTMLInputElement>(null);
  const [filename, setFilename] = useState<string | null>(null);
  const queryClient = useQueryClient();

  const mutation = useMutation<DocumentPublic, Error, File>({
    mutationFn: (file) => api.uploadDocument(file),
    onSuccess: () => {
      // invalidate any cached search results so the new doc appears
      queryClient.invalidateQueries({ queryKey: ["search"] });
    },
  });

  const onPickFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0] ?? null;
    setFilename(f?.name ?? null);
  };

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const f = inputRef.current?.files?.[0];
    if (!f) return;
    mutation.mutate(f);
  };

  const reset = () => {
    if (inputRef.current) inputRef.current.value = "";
    setFilename(null);
    mutation.reset();
  };

  return (
    <form
      onSubmit={onSubmit}
      className="flex flex-col gap-3 rounded-2xl border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-900"
    >
      <h2 className="text-base font-semibold">Upload a document</h2>
      <p className="text-xs text-zinc-500">
        PDF, DOCX, or TXT. Text is extracted automatically.
      </p>

      <input
        ref={inputRef}
        type="file"
        accept=".pdf,.docx,.txt"
        onChange={onPickFile}
        disabled={mutation.isPending}
        className="block w-full text-sm file:mr-3 file:rounded-md file:border-0 file:bg-zinc-900 file:px-3 file:py-2 file:text-sm file:text-white hover:file:bg-zinc-800 dark:file:bg-zinc-100 dark:file:text-zinc-900"
      />

      {filename && (
        <p className="truncate text-xs text-zinc-500">selected: {filename}</p>
      )}

      {mutation.isError && (
        <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-950 dark:text-red-300">
          {mutation.error instanceof ApiError
            ? mutation.error.message
            : "upload failed"}
        </p>
      )}

      {mutation.isSuccess && (
        <div className="rounded-md bg-emerald-50 px-3 py-2 text-sm text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300">
          Uploaded <strong>{mutation.data.filename}</strong> (
          {mutation.data.status}, {mutation.data.size_bytes} B).
        </div>
      )}

      <div className="flex gap-2">
        <button
          type="submit"
          disabled={!filename || mutation.isPending}
          className="rounded-md bg-zinc-900 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-zinc-800 disabled:opacity-50 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-zinc-200"
        >
          {mutation.isPending ? "Uploading…" : "Upload"}
        </button>
        {(mutation.isSuccess || mutation.isError) && (
          <button
            type="button"
            onClick={reset}
            className="rounded-md border border-zinc-300 px-3 py-2 text-sm transition-colors hover:bg-zinc-100 dark:border-zinc-700 dark:hover:bg-zinc-800"
          >
            Reset
          </button>
        )}
      </div>
    </form>
  );
}
