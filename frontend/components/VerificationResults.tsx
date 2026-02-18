"use client";

import { useState } from "react";

export type ClaimVerification = {
  claim: string;
  verdict: string;
  confidence: number;
  explanation: string;
  sources: string[];
};

const VERDICT_STYLES: Record<string, string> = {
  True: "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-200 border-emerald-300 dark:border-emerald-700",
  "Mostly True": "bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-200 border-green-300 dark:border-green-700",
  Misleading: "bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-200 border-amber-300 dark:border-amber-700",
  False: "bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-200 border-red-300 dark:border-red-700",
  Unverifiable: "bg-zinc-100 text-zinc-600 dark:bg-zinc-800 dark:text-zinc-300 border-zinc-300 dark:border-zinc-600",
};

function getVerdictClass(verdict: string): string {
  return VERDICT_STYLES[verdict] ?? VERDICT_STYLES.Unverifiable;
}

function domainFromUrl(url: string): string {
  try {
    const u = new URL(url);
    return u.hostname;
  } catch {
    return url;
  }
}

const EXPLANATION_TRUNCATE_LEN = 200;

function ClaimCard({ claim }: { claim: ClaimVerification }) {
  const [expanded, setExpanded] = useState(false);
  const isLong = claim.explanation.length > EXPLANATION_TRUNCATE_LEN;
  const showText = expanded || !isLong ? claim.explanation : claim.explanation.slice(0, EXPLANATION_TRUNCATE_LEN) + "…";

  return (
    <article className="rounded-xl border border-zinc-200 bg-white p-4 shadow-sm dark:border-zinc-700 dark:bg-zinc-900 sm:p-5">
      <p className="mb-3 text-base font-medium text-zinc-900 dark:text-zinc-100">
        {claim.claim}
      </p>
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <span
          className={`inline-flex rounded-full border px-3 py-0.5 text-sm font-medium ${getVerdictClass(claim.verdict)}`}
        >
          {claim.verdict}
        </span>
        <span className="text-sm text-zinc-500 dark:text-zinc-400">
          Confidence: {claim.confidence}%
        </span>
      </div>
      <div className="mb-2 h-2 w-full overflow-hidden rounded-full bg-zinc-200 dark:bg-zinc-700">
        <div
          className="h-full rounded-full bg-blue-500 transition-all duration-300"
          style={{ width: `${claim.confidence}%` }}
        />
      </div>
      <div className="mb-4">
        <p className="text-sm text-zinc-600 dark:text-zinc-300">
          {showText}
          {isLong && (
            <button
              type="button"
              onClick={() => setExpanded(!expanded)}
              className="ml-1 font-medium text-blue-600 hover:underline dark:text-blue-400"
            >
              {expanded ? " Show less" : " Show more"}
            </button>
          )}
        </p>
      </div>
      {claim.sources.length > 0 && (
        <div className="flex flex-wrap gap-2">
          <span className="text-xs font-medium text-zinc-500 dark:text-zinc-400">
            Sources:
          </span>
          {claim.sources.map((url, i) => (
            <a
              key={i}
              href={url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm text-blue-600 hover:underline dark:text-blue-400"
            >
              {domainFromUrl(url)}
            </a>
          ))}
        </div>
      )}
    </article>
  );
}

export function VerificationResults({ claims }: { claims: ClaimVerification[] }) {
  if (claims.length === 0) {
    return (
      <p className="rounded-lg border border-zinc-200 bg-white p-4 text-zinc-600 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-400">
        No verifiable claims found in the text.
      </p>
    );
  }

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold text-zinc-900 dark:text-zinc-100">
        Results
      </h2>
      <div className="flex flex-col gap-4">
        {claims.map((c, i) => (
          <ClaimCard key={i} claim={c} />
        ))}
      </div>
    </div>
  );
}
