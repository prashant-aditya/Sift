"use client";

import Link from "next/link";
import { LogIn } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ThemeToggle } from "@/components/shared/ThemeToggle";
import { NotificationBell } from "@/components/shared/NotificationBell";
import { UserMenu } from "@/components/auth/UserMenu";
import { useAuth } from "@/hooks/useAuth";

interface HeaderProps {
  mobileNavSlot?: React.ReactNode;
  sidebarToggleSlot?: React.ReactNode;
}

export function Header({ mobileNavSlot, sidebarToggleSlot }: HeaderProps) {
  const { isAuthenticated, isLoading: authLoading } = useAuth();

  return (
    <header
      className="flex h-12 shrink-0 items-center gap-2 border-b border-border px-4"
      role="banner"
    >
      {sidebarToggleSlot}
      {mobileNavSlot}

      <Link
        href="/"
        className="text-sm font-semibold tracking-wide text-foreground hover:text-foreground/80 transition-colors"
        aria-label="Sift — Go to home"
      >
        Sift
      </Link>

      <div className="ml-auto flex items-center gap-1">
        {!authLoading && isAuthenticated && <NotificationBell />}
        <ThemeToggle />
        {!authLoading &&
          (isAuthenticated ? (
            <UserMenu />
          ) : (
            <Link href="/auth/login">
              <Button variant="ghost" size="sm" className="touch-target">
                <LogIn className="size-4" />
                Sign in
              </Button>
            </Link>
          ))}
      </div>
    </header>
  );
}
