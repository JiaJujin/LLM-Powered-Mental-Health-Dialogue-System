/**
 * frontend/src/lib/insightsCache.ts
 *
 * Two-tier in-memory + sessionStorage cache for the Insights page.
 *
 * Tier 1 — module-level memory:
 *   Survives React re-renders within the same component lifecycle.
 *
 * Tier 2 — sessionStorage:
 *   Survives page refreshes (F5) within the same browser tab session.
 *   The sessionStorage key includes anonId so multiple users on the same
 *   browser are isolated from each other.
 *
 * Priority on read:  memory → sessionStorage → null
 * Write: always update both tiers.
 */

import type { InsightsResponse } from "../types";

export interface InsightsCache {
  analysis: InsightsResponse;
  /** Unix ms timestamp when this cache was populated */
  cachedAt: number;
}

const SESSION_KEY_PREFIX = "mindjournal_insights_";

// ── Module-level memory cache ────────────────────────────────────────────────
const _memory: Record<string, InsightsCache> = {};

function _mkSessionKey(anonId: string): string {
  return `${SESSION_KEY_PREFIX}${anonId}`;
}

function _readSession(anonId: string): InsightsCache | null {
  try {
    const raw = sessionStorage.getItem(_mkSessionKey(anonId));
    if (!raw) return null;
    return JSON.parse(raw) as InsightsCache;
  } catch {
    return null;
  }
}

function _writeSession(anonId: string, entry: InsightsCache): void {
  try {
    sessionStorage.setItem(_mkSessionKey(anonId), JSON.stringify(entry));
  } catch {
    // sessionStorage unavailable (private browsing, quota exceeded) — ignore
  }
}

function _clearSession(anonId: string): void {
  try {
    sessionStorage.removeItem(_mkSessionKey(anonId));
  } catch {
    // ignore
  }
}

// ── Public API ───────────────────────────────────────────────────────────────

export function getInsightsCache(anonId: string): InsightsCache | null {
  // Tier 1: in-memory
  if (_memory[anonId]) return _memory[anonId];

  // Tier 2: sessionStorage (survives page refresh)
  const fromSession = _readSession(anonId);
  if (fromSession) {
    // Promote to memory tier so subsequent renders are instant
    _memory[anonId] = fromSession;
    return fromSession;
  }

  return null;
}

export function setInsightsCache(anonId: string, analysis: InsightsResponse): void {
  const entry: InsightsCache = { analysis, cachedAt: Date.now() };
  _memory[anonId] = entry;
  _writeSession(anonId, entry);
}

export function clearInsightsCache(anonId: string): void {
  delete _memory[anonId];
  _clearSession(anonId);
}
