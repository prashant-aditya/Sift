"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { apiFetch } from "@/lib/api";
import type { Notification } from "@/types/notification";

const POLL_MS = 60_000;

interface UseNotificationsReturn {
  notifications: Notification[];
  unreadCount: number;
  markAsRead: (id: string) => Promise<void>;
  isLoading: boolean;
}

export function useNotifications(): UseNotificationsReturn {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const hasFetched = useRef(false);

  const fetchNotifications = useCallback(async () => {
    setIsLoading(true);
    try {
      const data = await apiFetch<Notification[]>("/api/v1/notifications", {
        method: "GET",
      });
      setNotifications(Array.isArray(data) ? data : []);
    } catch {
      // Graceful fallback: no notifications when API is unavailable.
      setNotifications((prev) => prev);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (hasFetched.current) return;
    hasFetched.current = true;

    let cancelled = false;
    const run = async () => {
      if (cancelled) return;
      await fetchNotifications();
    };

    run();

    const id = window.setInterval(() => {
      if (!cancelled) fetchNotifications();
    }, POLL_MS);

    return () => {
      cancelled = true;
      window.clearInterval(id);
    };
  }, [fetchNotifications]);

  const unreadCount = useMemo(
    () => notifications.filter((n) => !n.is_read).length,
    [notifications],
  );

  const markAsRead = useCallback(async (id: string) => {
    setNotifications((prev) =>
      prev.map((n) => (n.id === id ? { ...n, is_read: true } : n)),
    );

    try {
      await apiFetch(`/api/v1/notifications/${encodeURIComponent(id)}/read`, {
        method: "PATCH",
      });
    } catch {
      // If the backend fails, revert optimistic update.
      setNotifications((prev) =>
        prev.map((n) => (n.id === id ? { ...n, is_read: false } : n)),
      );
    }
  }, []);

  return { notifications, unreadCount, markAsRead, isLoading };
}

