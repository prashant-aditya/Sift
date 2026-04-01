"use client";

import { useMemo } from "react";
import { useRouter } from "next/navigation";
import {
  Bell,
  Lightbulb,
  RefreshCw,
  AlertTriangle,
  Check,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useNotifications } from "@/hooks/useNotifications";
import type { Notification } from "@/types/notification";

function iconForType(type: Notification["type"]) {
  const t = (type ?? "").toString().toLowerCase();
  if (t === "proactive_research") return Lightbulb;
  if (t === "knowledge_update") return RefreshCw;
  if (t === "contradiction_found") return AlertTriangle;
  return Bell;
}

function formatTimestamp(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  return d.toLocaleString(undefined, {
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function getNotificationHref(n: Notification): string {
  if (n.session_id) return `/session/${encodeURIComponent(n.session_id)}`;
  if (n.suggestion_id)
    return `/dashboard?suggestion=${encodeURIComponent(n.suggestion_id)}`;
  return "/dashboard";
}

export function NotificationBell() {
  const router = useRouter();
  const { notifications, unreadCount, markAsRead, isLoading } =
    useNotifications();

  const recent = useMemo(() => notifications.slice(0, 10), [notifications]);

  async function onNotificationClick(n: Notification) {
    if (!n.is_read) await markAsRead(n.id);
    router.push(getNotificationHref(n));
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        render={
          <Button
            variant="ghost"
            size="icon"
            className="touch-target relative"
            aria-label={
              unreadCount > 0
                ? `Notifications (${unreadCount} unread)`
                : "Notifications"
            }
            aria-busy={isLoading ? "true" : undefined}
          />
        }
      >
        <Bell className="h-5 w-5" />
        {unreadCount > 0 && (
          <span
            className="absolute -right-0.5 -top-0.5 inline-flex min-w-4 items-center justify-center rounded-full bg-destructive px-1 text-[10px] font-semibold leading-4 text-destructive-foreground"
            aria-hidden="true"
          >
            {unreadCount > 99 ? "99+" : unreadCount}
          </span>
        )}
      </DropdownMenuTrigger>

      <DropdownMenuContent align="end" side="bottom" sideOffset={8}>
        <DropdownMenuLabel>Notifications</DropdownMenuLabel>
        <DropdownMenuSeparator />

        {recent.length === 0 ? (
          <div className="px-2 py-2 text-sm text-muted-foreground">
            You’re all caught up.
          </div>
        ) : (
          recent.map((n) => {
            const Icon = iconForType(n.type);
            const ts = formatTimestamp(n.created_at);
            return (
              <DropdownMenuItem
                key={n.id}
                onClick={() => onNotificationClick(n)}
                className="flex items-start gap-2"
              >
                <div className="mt-0.5 flex size-5 items-center justify-center">
                  <Icon className="size-4" />
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="truncate font-medium">{n.title}</span>
                    {!n.is_read && (
                      <span className="ml-auto inline-flex items-center gap-1 text-xs text-muted-foreground">
                        <span className="size-1.5 rounded-full bg-destructive" />
                        Unread
                      </span>
                    )}
                    {n.is_read && (
                      <span className="ml-auto inline-flex items-center gap-1 text-xs text-muted-foreground">
                        <Check className="size-3.5" />
                        Read
                      </span>
                    )}
                  </div>
                  <div className="line-clamp-2 text-xs text-muted-foreground">
                    {n.body}
                  </div>
                  {ts && (
                    <div className="mt-1 text-[11px] text-muted-foreground/80">
                      {ts}
                    </div>
                  )}
                </div>
              </DropdownMenuItem>
            );
          })
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

