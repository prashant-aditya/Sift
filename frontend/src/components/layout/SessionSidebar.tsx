"use client";

import { useState, useMemo } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  Plus,
  Search,
  MessageSquare,
  Archive,
  Loader2,
} from "lucide-react";
import {
  isToday,
  isYesterday,
  differenceInCalendarDays,
} from "date-fns";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Skeleton } from "@/components/ui/skeleton";
import { cn, formatRelativeTime } from "@/lib/utils";
import { ROUTES } from "@/lib/constants";
import type { Session } from "@/types/session";

interface DateGroup {
  label: string;
  sessions: Session[];
}

function groupSessionsByDate(sessions: Session[]): DateGroup[] {
  const groups: Record<string, Session[]> = {
    Today: [],
    Yesterday: [],
    "This Week": [],
    Older: [],
  };

  for (const session of sessions) {
    const date = new Date(session.updated_at);
    if (isToday(date)) {
      groups["Today"].push(session);
    } else if (isYesterday(date)) {
      groups["Yesterday"].push(session);
    } else if (differenceInCalendarDays(new Date(), date) <= 7) {
      groups["This Week"].push(session);
    } else {
      groups["Older"].push(session);
    }
  }

  return (["Today", "Yesterday", "This Week", "Older"] as const)
    .filter((label) => groups[label].length > 0)
    .map((label) => ({
      label,
      sessions: groups[label].sort(
        (a, b) =>
          new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime(),
      ),
    }));
}

interface SessionSidebarProps {
  sessions: Session[];
  isLoading: boolean;
  onArchive: (id: string) => void;
  onNavigate?: () => void;
  className?: string;
}

export function SessionSidebar({
  sessions,
  isLoading,
  onArchive,
  onNavigate,
  className,
}: SessionSidebarProps) {
  const router = useRouter();
  const [search, setSearch] = useState("");

  const filtered = useMemo(() => {
    if (!search.trim()) return sessions;
    const q = search.toLowerCase();
    return sessions.filter((s) => s.title.toLowerCase().includes(q));
  }, [sessions, search]);

  const groups = useMemo(() => groupSessionsByDate(filtered), [filtered]);

  return (
    <nav
      aria-label="Session history"
      className={cn("flex h-full flex-col", className)}
    >
      <div className="flex flex-col gap-3 p-4">
        <Button
          variant="default"
          size="sm"
          className="w-full justify-start gap-2"
          onClick={() => {
            router.push(ROUTES.home);
            onNavigate?.();
          }}
        >
          <Plus className="size-4" data-icon="inline-start" />
          New Research
        </Button>

        <div className="relative">
          <Search className="pointer-events-none absolute left-2.5 top-1/2 size-3.5 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search sessions..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-8 h-8 text-sm"
            aria-label="Filter sessions"
          />
        </div>
      </div>

      <ScrollArea className="flex-1 overflow-hidden">
        <div className="px-2 pb-4">
          {isLoading ? (
            <div className="flex flex-col gap-2 px-2">
              {Array.from({ length: 5 }).map((_, i) => (
                <div key={i} className="flex flex-col gap-1.5 py-2">
                  <Skeleton className="h-4 w-3/4" />
                  <Skeleton className="h-3 w-1/2" />
                </div>
              ))}
            </div>
          ) : groups.length === 0 ? (
            <p className="px-4 py-8 text-center text-sm text-muted-foreground">
              {search ? "No sessions match your search." : "No research sessions yet."}
            </p>
          ) : (
            groups.map((group) => (
              <div key={group.label} className="mb-2">
                <h3 className="mb-1 px-3 pt-2 text-xs font-medium uppercase tracking-wider text-muted-foreground">
                  {group.label}
                </h3>
                <ul role="list">
                  {group.sessions.map((session) => (
                    <SessionItem
                      key={session.id}
                      session={session}
                      onArchive={onArchive}
                      onNavigate={onNavigate}
                    />
                  ))}
                </ul>
              </div>
            ))
          )}
        </div>
      </ScrollArea>
    </nav>
  );
}

interface SessionItemProps {
  session: Session;
  onArchive: (id: string) => void;
  onNavigate?: () => void;
}

function SessionItem({ session, onArchive, onNavigate }: SessionItemProps) {
  const [archiving, setArchiving] = useState(false);

  const handleArchive = async (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setArchiving(true);
    onArchive(session.id);
  };

  return (
    <li>
      <Link
        href={ROUTES.session(session.id)}
        onClick={() => onNavigate?.()}
        className={cn(
          "group flex w-full items-start gap-3 rounded-lg px-3 py-2.5",
          "text-left text-sm transition-colors",
          "hover:bg-sidebar-accent hover:text-sidebar-accent-foreground",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
        )}
      >
        <MessageSquare className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
        <div className="flex min-w-0 flex-1 flex-col gap-1">
          <span className="truncate font-medium leading-tight">
            {session.title}
          </span>
          <div className="flex items-center gap-2">
            <span className="text-xs text-muted-foreground">
              {formatRelativeTime(session.updated_at)}
            </span>
            <Badge variant="secondary" className="h-4 px-1.5 text-[10px]">
              {session.query_count}
            </Badge>
          </div>
        </div>
        <button
          type="button"
          onClick={handleArchive}
          disabled={archiving}
          className={cn(
            "mt-0.5 shrink-0 rounded-md p-1 text-muted-foreground",
            "opacity-0 transition-opacity group-hover:opacity-100",
            "hover:bg-destructive/10 hover:text-destructive",
            "focus-visible:opacity-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
          )}
          aria-label={`Archive "${session.title}"`}
        >
          {archiving ? (
            <Loader2 className="size-3.5 animate-spin" />
          ) : (
            <Archive className="size-3.5" />
          )}
        </button>
      </Link>
    </li>
  );
}
