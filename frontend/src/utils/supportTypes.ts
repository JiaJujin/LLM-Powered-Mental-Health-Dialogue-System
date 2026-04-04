/**
 * Shared types for the user-facing "My Support" page.
 */

export interface Supporter {
  name: string;
  fullName: string;
  role: string;
  department: string;
  initials: string;
  avatarColor: string;
  status: "online" | "busy" | "offline";
  statusLabel: string;
  bio: string;
}

export interface SupportNotification {
  id: string;
  timestamp: string; // ISO 8601
  source: "diary" | "chat";
  message: string;
  isRead: boolean;
}
