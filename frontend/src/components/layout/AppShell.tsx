"use client";

import { useState, useCallback } from "react";
import { PanelLeftClose, PanelLeft } from "lucide-react";

import { Button } from "@/components/ui/button";
import { SessionSidebar } from "@/components/layout/SessionSidebar";
import { Header } from "@/components/layout/Header";
import { MobileNav } from "@/components/layout/MobileNav";
import { useSession } from "@/hooks/useSession";
import { useAuth } from "@/hooks/useAuth";
import { cn } from "@/lib/utils";

const SIDEBAR_WIDTH = 280;

interface AppShellProps {
  children: React.ReactNode;
}

export function AppShell({ children }: AppShellProps) {
  const [collapsed, setCollapsed] = useState(false);
  const { sessions, isLoading, archiveSession } = useSession();
  const { isAuthenticated, isLoading: authLoading } = useAuth();

  const toggleCollapsed = useCallback(() => setCollapsed((c) => !c), []);

  const showSidebar = isAuthenticated && !authLoading;

  const sidebarToggle = showSidebar && collapsed ? (
    <Button
      variant="ghost"
      size="icon-sm"
      onClick={toggleCollapsed}
      className="hidden lg:inline-flex"
      aria-label="Expand sidebar"
    >
      <PanelLeft className="size-4" />
    </Button>
  ) : null;

  const mobileNav = showSidebar ? (
    <MobileNav
      sessions={sessions}
      isLoading={isLoading}
      onArchive={archiveSession}
    />
  ) : null;

  return (
    <div className="relative flex h-dvh overflow-hidden bg-background">
      {showSidebar && (
        <aside
          className={cn(
            "hidden lg:flex flex-col border-r border-sidebar-border bg-sidebar",
            "transition-[width] duration-200 ease-in-out",
          )}
          style={{ width: collapsed ? 0 : SIDEBAR_WIDTH }}
          aria-label="Session sidebar"
        >
          <div
            className="flex h-full flex-col overflow-hidden"
            style={{ width: SIDEBAR_WIDTH }}
          >
            <div className="flex items-center justify-between border-b border-sidebar-border px-4 py-3">
              <span className="text-sm font-semibold text-sidebar-foreground tracking-wide">
                Sessions
              </span>
              <Button
                variant="ghost"
                size="icon-sm"
                onClick={toggleCollapsed}
                aria-label="Collapse sidebar"
              >
                <PanelLeftClose className="size-4" />
              </Button>
            </div>
            <SessionSidebar
              sessions={sessions}
              isLoading={isLoading}
              onArchive={archiveSession}
            />
          </div>
        </aside>
      )}

      <div className="flex flex-1 flex-col overflow-hidden">
        <Header
          sidebarToggleSlot={sidebarToggle}
          mobileNavSlot={mobileNav}
        />
        <main className="flex-1 overflow-y-auto">{children}</main>
      </div>
    </div>
  );
}
