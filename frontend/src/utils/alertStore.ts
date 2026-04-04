/**
 * Alert store — singleton state for CrisisAlert objects.
 *
 * Architecture:
 * - alertStore   → plain mutable object (accessible from anywhere, no context needed)
 * - useAlertStore → React hook that triggers re-renders when alerts change
 *
 * Usage:
 *   import { alertStore } from "./alertStore";
 *
 *   // Add an alert (fire-and-forget in ChatJournalPage):
 *   const alert = await detectCrisis(...);
 *   if (alert) alertStore.addAlert(alert);
 *
 *   // In a component that needs to re-render:
 *   const { alerts, unreadCount } = useAlertStore();
 */

import { useState, useCallback } from "react";
import type { CrisisAlert, CrisisLevel } from "./crisisTypes";

export { type CrisisLevel } from "./crisisTypes";

// ---------------------------------------------------------------------------
// Store (singleton — mutations trigger React re-renders via useState)
// ---------------------------------------------------------------------------

const _alerts: CrisisAlert[] = [];

const _store = {
  _listeners: new Set<() => void>(),

  get alerts(): CrisisAlert[] {
    return _alerts;
  },

  get unreadCount(): number {
    return _alerts.filter((a) => !a.isRead).length;
  },

  addAlert(alert: CrisisAlert): void {
    _alerts.unshift(alert); // newest first
    this._notify();
  },

  markAsRead(id: string): void {
    const a = _alerts.find((x) => x.id === id);
    if (a) {
      a.isRead = true;
      this._notify();
    }
  },

  markAllAsRead(): void {
    _alerts.forEach((a) => (a.isRead = true));
    this._notify();
  },

  _notify(): void {
    _store._listeners.forEach((fn) => fn());
  },
};

export const alertStore = _store;

// ---------------------------------------------------------------------------
// React hook — subscribes to store changes so components re-render
// ---------------------------------------------------------------------------

export function useAlertStore() {
  const [, forceUpdate] = useState(0);

  // Subscribe on mount, unsubscribe on unmount
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const notify = useCallback(() => forceUpdate((n) => n + 1), []);
  _store._listeners.add(notify);

  // Return a stable snapshot copy each render
  const alerts = _store.alerts.slice(); // shallow copy
  const unreadCount = _store.unreadCount;

  return {
    alerts,
    unreadCount,
    addAlert: _store.addAlert.bind(_store),
    markAsRead: _store.markAsRead.bind(_store),
    markAllAsRead: _store.markAllAsRead.bind(_store),
  };
}
