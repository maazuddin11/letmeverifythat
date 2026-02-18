"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import Link from "next/link";
import { VerificationResults } from "@/components/VerificationResults";
import { getHistoryEntry, type HistoryEntry } from "@/lib/history";

export default function ResultsPage() {
  const params = useParams();
  const id = typeof params.id === "string" ? params.id : "";
  const [entry, setEntry] = useState<HistoryEntry | null | "loading">("loading");
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!id) {
      setEntry(null);
      return;
    }
    const found = getHistoryEntry(id);
    setEntry(found ?? null);
  }, [id]);

  function copyLink() {
    if (typeof window === "undefined" || !id) return;
    const url = `${window.location.origin}/results/${id}`;
    navigator.clipboard.writeText(url).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }

  if (entry === "loading") {
    return (
      <div className="flex min-h-screen items-center justify-center bg-zinc-50 dark:bg-zinc-950">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-blue-500 border-t-transparent" />
      </div>
    );
  }

  if (entry === null) {
    return (
      <div className="min-h-screen bg-zinc-50 dark:bg-zinc-950">
        <main className="mx-auto max-w-2xl px-4 py-12 sm:px-6 text-center">
          <h1 className="mb-4 text-xl font-semibold text-zinc-900 dark:text-zinc-100">
            Results not found
          </h1>
          <p className="mb-6 text-zinc-600 dark:text-zinc-400">
            These results may have been cleared or this link was opened on a different device. Run a new verification from the home page.
          </p>
          <Link
            href="/"
            className="inline-flex rounded-lg bg-blue-600 px-4 py-2 font-medium text-white hover:bg-blue-700"
          >
            Verify something new
          </Link>
        </main>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-zinc-950">
      <main className="mx-auto max-w-2xl px-4 py-8 sm:px-6">
        <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
          <Link
            href="/"
            className="text-sm font-medium text-blue-600 hover:underline dark:text-blue-400"
          >
            ← LetMeVerifyThat
          </Link>
          <button
            type="button"
            onClick={copyLink}
            className="rounded-lg border border-zinc-300 bg-white px-3 py-2 text-sm font-medium text-zinc-700 hover:bg-zinc-50 dark:border-zinc-600 dark:bg-zinc-900 dark:text-zinc-200 dark:hover:bg-zinc-800"
          >
            {copied ? "Copied!" : "Copy link"}
          </button>
        </div>
        <VerificationResults claims={entry.results.claims} />
      </main>
    </div>
  );
}
