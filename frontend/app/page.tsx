"use client";

import { useState, useEffect, useCallback } from "react";
import { VerificationResults } from "@/components/VerificationResults";
import {
  getHistoryList,
  saveToHistory,
  clearHistory,
  truncateForDisplay,
  type HistoryEntry,
  type VerifyResponse,
} from "@/lib/history";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

function useHistory() {
  const [list, setList] = useState<HistoryEntry[]>([]);

  const refresh = useCallback(() => {
    setList(getHistoryList());
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return { list, refresh };
}

export default function Home() {
  const [text, setText] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [results, setResults] = useState<VerifyResponse | null>(null);
  const [currentResultId, setCurrentResultId] = useState<string | null>(null);
  const { list: historyList, refresh: refreshHistory } = useHistory();

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setResults(null);
    setCurrentResultId(null);
    if (!text.trim()) return;
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/verify`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: text.trim() }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error((err as { detail?: string }).detail ?? res.statusText);
      }
      const data: VerifyResponse = await res.json();
      const id = crypto.randomUUID();
      saveToHistory({
        id,
        text: text.trim(),
        results: data,
      });
      refreshHistory();
      setResults(data);
      setCurrentResultId(id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Verification failed");
    } finally {
      setLoading(false);
    }
  }

  function loadFromHistory(entry: HistoryEntry) {
    setResults(entry.results);
    setCurrentResultId(entry.id);
    setError(null);
  }

  function handleClearHistory() {
    clearHistory();
    refreshHistory();
    if (results && currentResultId && historyList.some((e) => e.id === currentResultId)) {
      setResults(null);
      setCurrentResultId(null);
    }
  }

  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-zinc-950">
      <main className="mx-auto max-w-2xl px-4 py-8 sm:px-6">
        <h1 className="mb-8 text-center text-2xl font-bold text-zinc-900 dark:text-zinc-100 sm:text-3xl">
          LetMeVerifyThat
        </h1>

        <form onSubmit={handleSubmit} className="space-y-4">
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder={"Paste claims, an article URL, or both — e.g.\n\nhttps://example.com/health-article\nAlso, someone told me MSG causes headaches"}
            className="min-h-[160px] w-full resize-y rounded-lg border border-zinc-300 bg-white px-4 py-3 text-zinc-900 placeholder-zinc-500 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 dark:border-zinc-600 dark:bg-zinc-900 dark:text-zinc-100 dark:placeholder-zinc-400"
            disabled={loading}
          />
          <button
            type="submit"
            disabled={loading || !text.trim()}
            className="w-full rounded-lg bg-blue-600 px-4 py-3 font-medium text-white transition-colors hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50 sm:min-w-[140px] sm:w-auto"
          >
            {loading ? (
              <span className="flex items-center justify-center gap-2">
                <span className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                Verifying…
              </span>
            ) : (
              "Verify"
            )}
          </button>
        </form>

        {error && (
          <div className="mt-6 rounded-lg border border-red-200 bg-red-50 p-4 text-red-800 dark:border-red-800 dark:bg-red-950/30 dark:text-red-200">
            {error}
          </div>
        )}

        <section className="mt-8">
          {historyList.length > 0 ? (
            <>
              <div className="mb-3 flex items-center justify-between">
                <h2 className="text-lg font-semibold text-zinc-900 dark:text-zinc-100">
                  Recent Verifications
                </h2>
                <button
                  type="button"
                  onClick={handleClearHistory}
                  className="text-sm text-zinc-500 hover:text-zinc-700 dark:text-zinc-400 dark:hover:text-zinc-200"
                >
                  Clear history
                </button>
              </div>
              <ul className="space-y-2">
                {historyList.map((entry) => (
                  <li key={entry.id}>
                    <button
                      type="button"
                      onClick={() => loadFromHistory(entry)}
                      className={`w-full rounded-lg border px-3 py-2 text-left text-sm transition-colors ${
                        currentResultId === entry.id
                          ? "border-blue-500 bg-blue-50 dark:border-blue-600 dark:bg-blue-950/30"
                          : "border-zinc-200 bg-white hover:bg-zinc-50 dark:border-zinc-700 dark:bg-zinc-900 dark:hover:bg-zinc-800"
                      }`}
                    >
                      <span className="text-zinc-600 dark:text-zinc-300">
                        {truncateForDisplay(entry.text)}
                      </span>
                      <span className="ml-2 text-xs text-zinc-400 dark:text-zinc-500">
                        {new Date(entry.timestamp).toLocaleDateString()}
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            </>
          ) : (
            !loading &&
            !results && (
              <p className="rounded-lg border border-zinc-200 bg-white px-4 py-6 text-center text-sm text-zinc-500 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-400">
                No recent verifications yet. Paste text above and click Verify to get started.
              </p>
            )
          )}
        </section>

        {results && (
          <div className="mt-8 animate-results-in">
            {currentResultId && (
              <div className="mb-4 flex items-center gap-2">
                <a
                  href={`/results/${currentResultId}`}
                  className="text-sm text-blue-600 hover:underline dark:text-blue-400"
                >
                  Share results
                </a>
              </div>
            )}
            <VerificationResults claims={results.claims} />
          </div>
        )}
      </main>
    </div>
  );
}
