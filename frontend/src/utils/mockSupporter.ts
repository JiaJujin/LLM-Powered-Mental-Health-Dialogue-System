/**
 * Mock assigned supporter — in production, this would be fetched from the backend
 * based on the authenticated user's assignment.
 */
import { Supporter } from "./supportTypes";

export const ASSIGNED_SUPPORTER: Supporter = {
  name: "Miss Chan",
  fullName: "Chan Tsz Yan",
  role: "Student Counselling Director",
  department: "Student Affairs Office",
  initials: "MC",
  avatarColor: "#4A90A4",
  status: "online",
  statusLabel: "Available",
  bio: "Here to listen and support you, anytime you need.",
};
