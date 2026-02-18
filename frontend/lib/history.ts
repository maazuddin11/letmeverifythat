import type { ClaimVerification } from "@/components/VerificationResults";

export type VerifyResponse = { claims: ClaimVerification[] };

export type HistoryEntry = {
  id: string;
  text: string;
  timestamp: number;
  results: VerifyResponse;
};

const HISTORY_KEY = "letmeverifythat-history";
const MAX_HISTORY = 20;

function getHistory(): HistoryEntry[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(HISTORY_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as HistoryEntry[];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export function saveToHistory(entry: Omit<HistoryEntry, "timestamp">): void {
  const list = getHistory();
  const withTimestamp = { ...entry, timestamp: Date.now() };
  const next = [withTimestamp, ...list.filter((e) => e.id !== entry.id)].slice(
    0,
    MAX_HISTORY
  );
  localStorage.setItem(HISTORY_KEY, JSON.stringify(next));
}

export function getHistoryList(): HistoryEntry[] {
  return getHistory();
}

export function getHistoryEntry(id: string): HistoryEntry | null {
  return getHistory().find((e) => e.id === id) ?? null;
}

export function clearHistory(): void {
  localStorage.removeItem(HISTORY_KEY);
}

export function truncateForDisplay(text: string, max = 80): string {
  const t = text.trim();
  if (t.length <= max) return t;
  return t.slice(0, max).trim() + "…";
}
