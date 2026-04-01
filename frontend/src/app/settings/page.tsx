"use client";

import Link from "next/link";
import { useTheme } from "next-themes";
import { useSyncExternalStore } from "react";
import { ROUTES, SOURCES } from "@/lib/constants";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Checkbox } from "@/components/ui/checkbox";

const emptySubscribe = () => () => {};

function useIsClient() {
  return useSyncExternalStore(
    emptySubscribe,
    () => true,
    () => false,
  );
}

export default function SettingsPage() {
  const { theme, setTheme } = useTheme();
  const isClient = useIsClient();

  return (
    <div className="mx-auto w-full max-w-3xl p-6">
      <div className="mb-6 flex items-start justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">Settings</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Preferences for your Sift experience.
          </p>
        </div>

        <Link href={ROUTES.schedules}>
          <Button variant="outline">Manage schedules</Button>
        </Link>
      </div>

      <div className="space-y-4">
        <Card>
          <CardHeader>
            <CardTitle>Theme preference</CardTitle>
            <CardDescription>
              Choose how Sift should look on this device.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="max-w-xs">
              <Select
                value={isClient ? theme ?? "system" : "system"}
                onValueChange={(v) => setTheme(v ?? "system")}
                disabled={!isClient}
              >
                <SelectTrigger className="w-full">
                  <SelectValue placeholder="Select theme" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="system">System</SelectItem>
                  <SelectItem value="light">Light</SelectItem>
                  <SelectItem value="dark">Dark</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Default research sources (placeholder)</CardTitle>
            <CardDescription>
              This will control which sources are pre-selected for new research.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid gap-2 sm:grid-cols-2">
              {SOURCES.map((s) => (
                <label
                  key={s.name}
                  className="flex items-center gap-2 rounded-lg border border-border/60 bg-card/40 px-3 py-2 opacity-60"
                >
                  <Checkbox checked disabled aria-label={`${s.displayName} source`} />
                  <span className="text-sm">{s.displayName}</span>
                </label>
              ))}
            </div>
            <p className="mt-3 text-xs text-muted-foreground">
              Coming soon: save your default sources to your profile.
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

