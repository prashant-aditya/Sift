"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { Controller, useForm } from "react-hook-form";
import { Edit2, Trash2 } from "lucide-react";

import { ROUTES, SOURCES } from "@/lib/constants";
import type { ResearchSchedule, ScheduleFrequency, ScheduleInput } from "@/lib/schedules";
import { scheduleFrequencySchema } from "@/lib/schedules";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Checkbox } from "@/components/ui/checkbox";
import { Switch } from "@/components/ui/switch";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";

const scheduleFormSchema = z.object({
  query_template: z.string().trim().min(1, "Query template is required"),
  topics_raw: z.string().trim().min(1, "At least one topic is required"),
  frequency: scheduleFrequencySchema,
  sources: z.array(z.string()).min(1, "Select at least one source"),
});

type ScheduleFormValues = z.infer<typeof scheduleFormSchema>;

function parseTopics(raw: string): string[] {
  return raw
    .split(",")
    .map((t) => t.trim())
    .filter(Boolean);
}

function fmtLastRun(lastRun: string | null): string {
  if (!lastRun) return "Never";
  const d = new Date(lastRun);
  if (Number.isNaN(d.getTime())) return "—";
  return d.toLocaleString();
}

async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
  });
  if (!res.ok) {
    const body = (await res.json().catch(() => null)) as unknown;
    throw new Error(
      typeof body === "object" && body && "message" in body
        ? String((body as { message: unknown }).message)
        : `Request failed (${res.status})`,
    );
  }
  return (await res.json()) as T;
}

function ScheduleForm({
  submitLabel,
  defaultValues,
  onSubmit,
  submitting,
}: {
  submitLabel: string;
  defaultValues?: Partial<ScheduleFormValues>;
  onSubmit: (input: ScheduleInput) => Promise<void>;
  submitting: boolean;
}) {
  const {
    register,
    handleSubmit,
    control,
    formState: { errors },
    reset,
  } = useForm<ScheduleFormValues>({
    resolver: zodResolver(scheduleFormSchema),
    defaultValues: {
      query_template: "",
      topics_raw: "",
      frequency: "daily",
      sources: [],
      ...defaultValues,
    },
  });

  useEffect(() => {
    reset({
      query_template: "",
      topics_raw: "",
      frequency: "daily",
      sources: [],
      ...defaultValues,
    });
  }, [defaultValues, reset]);

  const sourceOptions = useMemo(() => SOURCES.map((s) => s.name), []);

  return (
    <form
      className="grid gap-4"
      onSubmit={handleSubmit(async (values) => {
        const input: ScheduleInput = {
          query_template: values.query_template.trim(),
          topics: parseTopics(values.topics_raw),
          frequency: values.frequency,
          sources: values.sources,
        };
        await onSubmit(input);
      })}
    >
      <div className="grid gap-1.5">
        <label className="text-sm font-medium" htmlFor="query_template">
          Query template
        </label>
        <Input
          id="query_template"
          placeholder='e.g. "Latest developments in {topic}"'
          {...register("query_template")}
          aria-invalid={!!errors.query_template}
        />
        {errors.query_template && (
          <p className="text-xs text-destructive">{errors.query_template.message}</p>
        )}
      </div>

      <div className="grid gap-1.5">
        <label className="text-sm font-medium" htmlFor="topics_raw">
          Topics
        </label>
        <Input
          id="topics_raw"
          placeholder="e.g. RAG systems, vector databases"
          {...register("topics_raw")}
          aria-invalid={!!errors.topics_raw}
        />
        {errors.topics_raw && (
          <p className="text-xs text-destructive">{errors.topics_raw.message}</p>
        )}
        <p className="text-xs text-muted-foreground">
          Comma-separated. Each run replaces <span className="font-mono">{"{topic}"}</span> in
          your template.
        </p>
      </div>

      <div className="grid gap-1.5">
        <label className="text-sm font-medium">Frequency</label>
        <Controller
          name="frequency"
          control={control}
          render={({ field }) => (
            <Select
              value={field.value}
              onValueChange={(v) => field.onChange(v as ScheduleFrequency)}
            >
              <SelectTrigger className="w-full">
                <SelectValue placeholder="Select frequency" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="daily">Daily</SelectItem>
                <SelectItem value="weekly">Weekly</SelectItem>
              </SelectContent>
            </Select>
          )}
        />
        {errors.frequency && (
          <p className="text-xs text-destructive">{errors.frequency.message}</p>
        )}
      </div>

      <div className="grid gap-2">
        <div>
          <p className="text-sm font-medium">Sources</p>
          {errors.sources && (
            <p className="mt-1 text-xs text-destructive">{errors.sources.message}</p>
          )}
        </div>

        <Controller
          name="sources"
          control={control}
          render={({ field }) => (
            <div className="grid gap-2 sm:grid-cols-2">
              {SOURCES.map((s) => {
                const checked = field.value?.includes(s.name) ?? false;
                return (
                  <label
                    key={s.name}
                    className="flex items-center gap-2 rounded-lg border border-border/60 bg-card/40 px-3 py-2"
                  >
                    <Checkbox
                      checked={checked}
                      onCheckedChange={(next) => {
                        const nextChecked = Boolean(next);
                        const set = new Set(field.value ?? []);
                        if (nextChecked) set.add(s.name);
                        else set.delete(s.name);
                        field.onChange(Array.from(set).filter((x) => sourceOptions.includes(x)));
                      }}
                      aria-label={`${s.displayName} source`}
                    />
                    <span className="text-sm">{s.displayName}</span>
                  </label>
                );
              })}
            </div>
          )}
        />
      </div>

      <div className="flex items-center justify-end gap-2">
        <Button type="submit" disabled={submitting}>
          {submitLabel}
        </Button>
      </div>
    </form>
  );
}

export default function SchedulesPage() {
  const [schedules, setSchedules] = useState<ResearchSchedule[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [savingEdit, setSavingEdit] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchJson<ResearchSchedule[]>("/api/v1/schedules", {
        cache: "no-store",
      });
      setSchedules(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load schedules");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const editingSchedule = useMemo(
    () => schedules.find((s) => s.id === editingId) ?? null,
    [schedules, editingId],
  );

  const createSchedule = useCallback(
    async (input: ScheduleInput) => {
      setCreating(true);
      setError(null);
      try {
        const created = await fetchJson<ResearchSchedule>("/api/v1/schedules", {
          method: "POST",
          body: JSON.stringify(input),
        });
        setSchedules((prev) => [created, ...prev]);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to create schedule");
      } finally {
        setCreating(false);
      }
    },
    [],
  );

  const patchSchedule = useCallback(async (id: string, patch: Partial<ScheduleInput> & { is_active?: boolean }) => {
    const updated = await fetchJson<ResearchSchedule>(`/api/v1/schedules/${id}`, {
      method: "PATCH",
      body: JSON.stringify(patch),
    });
    setSchedules((prev) => prev.map((s) => (s.id === id ? updated : s)));
  }, []);

  const deleteSchedule = useCallback(
    async (id: string) => {
      const ok = window.confirm("Delete this schedule?");
      if (!ok) return;
      setError(null);
      try {
        await fetchJson<{ ok: true }>(`/api/v1/schedules/${id}`, { method: "DELETE" });
        setSchedules((prev) => prev.filter((s) => s.id !== id));
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to delete schedule");
      }
    },
    [],
  );

  return (
    <div className="mx-auto w-full max-w-4xl p-6">
      <div className="mb-6 flex items-start justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">Research schedules</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Create daily or weekly briefings across your favorite sources.
          </p>
        </div>

        <Link href={ROUTES.settings}>
          <Button variant="outline">Back to settings</Button>
        </Link>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card className="h-fit">
          <CardHeader>
            <CardTitle>Create schedule</CardTitle>
            <CardDescription>
              Define a template and topics; Sift will run it on a cadence.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ScheduleForm
              submitLabel={creating ? "Creating..." : "Create schedule"}
              submitting={creating}
              onSubmit={createSchedule}
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Existing schedules</CardTitle>
            <CardDescription>Manage, pause, edit, or delete schedules.</CardDescription>
          </CardHeader>
          <CardContent>
            {error && (
              <div className="mb-3 rounded-lg border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
                {error}
              </div>
            )}

            {loading ? (
              <p className="text-sm text-muted-foreground">Loading…</p>
            ) : schedules.length === 0 ? (
              <p className="text-sm text-muted-foreground">No schedules yet.</p>
            ) : (
              <div className="grid gap-3">
                {schedules.map((s) => (
                  <div
                    key={s.id}
                    className="rounded-lg border border-border/60 bg-card/40 px-4 py-3"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <p className="truncate font-medium">{s.query_template}</p>
                        <p className="mt-1 text-xs text-muted-foreground">
                          <span className="font-medium text-foreground/80">Frequency:</span>{" "}
                          {s.frequency} ·{" "}
                          <span className="font-medium text-foreground/80">Last run:</span>{" "}
                          {fmtLastRun(s.last_run)}
                        </p>
                      </div>

                      <div className="flex items-center gap-2">
                        <div className="flex items-center gap-2">
                          <span className="sr-only">
                            {s.is_active ? "Active schedule" : "Paused schedule"}
                          </span>
                          <Switch
                            checked={s.is_active}
                            onCheckedChange={async (next) => {
                              try {
                                await patchSchedule(s.id, { is_active: Boolean(next) });
                              } catch (e) {
                                setError(
                                  e instanceof Error ? e.message : "Failed to update schedule",
                                );
                              }
                            }}
                            aria-label={s.is_active ? "Pause schedule" : "Resume schedule"}
                          />
                        </div>

                        <Dialog
                          open={editingId === s.id}
                          onOpenChange={(open) => setEditingId(open ? s.id : null)}
                        >
                          <DialogTrigger
                            render={
                              <Button
                                variant="outline"
                                size="icon-sm"
                                aria-label="Edit schedule"
                              />
                            }
                          >
                            <Edit2 className="size-4" />
                          </DialogTrigger>
                          <DialogContent className="sm:max-w-lg">
                            <DialogHeader>
                              <DialogTitle>Edit schedule</DialogTitle>
                              <DialogDescription>
                                Update your template, topics, frequency, or sources.
                              </DialogDescription>
                            </DialogHeader>

                            {editingSchedule && (
                              <ScheduleForm
                                submitLabel={savingEdit ? "Saving..." : "Save changes"}
                                submitting={savingEdit}
                                defaultValues={{
                                  query_template: editingSchedule.query_template,
                                  topics_raw: editingSchedule.topics.join(", "),
                                  frequency: editingSchedule.frequency,
                                  sources: editingSchedule.sources,
                                }}
                                onSubmit={async (input) => {
                                  setSavingEdit(true);
                                  setError(null);
                                  try {
                                    await patchSchedule(editingSchedule.id, input);
                                    setEditingId(null);
                                  } catch (e) {
                                    setError(
                                      e instanceof Error
                                        ? e.message
                                        : "Failed to update schedule",
                                    );
                                  } finally {
                                    setSavingEdit(false);
                                  }
                                }}
                              />
                            )}
                          </DialogContent>
                        </Dialog>

                        <Button
                          variant="destructive"
                          size="icon-sm"
                          onClick={() => void deleteSchedule(s.id)}
                          aria-label="Delete schedule"
                        >
                          <Trash2 className="size-4" />
                        </Button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}

            <div className="mt-4 flex items-center justify-end">
              <Button variant="ghost" size="sm" onClick={() => void load()}>
                Refresh
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

