/**
 * React Context + useReducer store for user-facing support notifications.
 *
 * Architecture:
 * - SupportNotificationProvider wraps the app in main.tsx
 * - useSupportNotifications() hook exposes notifications + unreadCount
 *
 * Usage:
 *   import { useSupportNotifications } from "../store/supportNotificationStore";
 *   const { state, addNotification, markAllRead } = useSupportNotifications();
 */

import { createContext, useContext, useReducer, useCallback, ReactNode } from "react";
import type { SupportNotification } from "../utils/supportTypes";

// ---------------------------------------------------------------------------
// State & reducer
// ---------------------------------------------------------------------------

interface StoreState {
  notifications: SupportNotification[];
  unreadCount: number;
}

type Action =
  | { type: "ADD"; notification: SupportNotification }
  | { type: "MARK_ALL_READ" };

function reducer(state: StoreState, action: Action): StoreState {
  switch (action.type) {
    case "ADD":
      console.log("[NOTIFICATION STORE] ADD action:", action.notification);
      return {
        notifications: [action.notification, ...state.notifications],
        unreadCount: state.unreadCount + 1,
      };
    case "MARK_ALL_READ":
      return {
        notifications: state.notifications.map((n) => ({ ...n, isRead: true })),
        unreadCount: 0,
      };
    default:
      return state;
  }
}

// ---------------------------------------------------------------------------
// Context
// ---------------------------------------------------------------------------

interface StoreContextValue {
  state: StoreState;
  addNotification: (n: SupportNotification) => void;
  markAllRead: () => void;
}

const StoreContext = createContext<StoreContextValue | null>(null);

// ---------------------------------------------------------------------------
// Provider
// ---------------------------------------------------------------------------

export function SupportNotificationProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(reducer, { notifications: [], unreadCount: 0 });

  const addNotification = useCallback(
    (n: SupportNotification) => dispatch({ type: "ADD", notification: n }),
    []
  );

  const markAllRead = useCallback(() => dispatch({ type: "MARK_ALL_READ" }), []);

  return (
    <StoreContext.Provider value={{ state, addNotification, markAllRead }}>
      {children}
    </StoreContext.Provider>
  );
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function useSupportNotifications(): StoreContextValue {
  const ctx = useContext(StoreContext);
  if (!ctx) {
    throw new Error("useSupportNotifications must be used inside SupportNotificationProvider");
  }
  return ctx;
}
