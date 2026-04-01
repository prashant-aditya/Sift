export type NotificationType =
  | "proactive_research"
  | "knowledge_update"
  | "contradiction_found"
  | (string & {});

export interface Notification {
  id: string;
  user_id?: string;
  type: NotificationType;
  title: string;
  body: string;
  suggestion_query?: string | null;
  is_read: boolean;
  created_at: string;

  // Optional fields (backend may include these for deep linking).
  session_id?: string | null;
  suggestion_id?: string | null;
}

