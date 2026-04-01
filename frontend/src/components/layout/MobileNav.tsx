"use client";

import { useState } from "react";
import { Menu } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetTrigger,
  SheetContent,
  SheetTitle,
} from "@/components/ui/sheet";
import { SessionSidebar } from "@/components/layout/SessionSidebar";
import type { Session } from "@/types/session";

interface MobileNavProps {
  sessions: Session[];
  isLoading: boolean;
  onArchive: (id: string) => void;
}

export function MobileNav({ sessions, isLoading, onArchive }: MobileNavProps) {
  const [open, setOpen] = useState(false);

  return (
    <div className="lg:hidden">
      <Sheet open={open} onOpenChange={setOpen}>
        <SheetTrigger
          render={
            <Button
              variant="ghost"
              size="icon-sm"
              aria-label="Open session menu"
            />
          }
        >
          <Menu className="size-4" />
        </SheetTrigger>
        <SheetContent
          side="left"
          className="w-full max-w-none sm:max-w-none p-0"
          showCloseButton
        >
          <SheetTitle className="sr-only">Session history</SheetTitle>
          <div className="flex h-full flex-col pt-10">
            <SessionSidebar
              sessions={sessions}
              isLoading={isLoading}
              onArchive={onArchive}
              onNavigate={() => setOpen(false)}
            />
          </div>
        </SheetContent>
      </Sheet>
    </div>
  );
}
