import type { ResearchSchedule, ScheduleInput } from "@/lib/schedules";

declare global {
  var __siftScheduleStore:
    | {
        schedules: ResearchSchedule[];
      }
    | undefined;
}

function nowIso(): string {
  return new Date().toISOString();
}

export function getScheduleStore(): { schedules: ResearchSchedule[] } {
  if (!globalThis.__siftScheduleStore) {
    globalThis.__siftScheduleStore = { schedules: [] };
  }
  return globalThis.__siftScheduleStore;
}

export function createSchedule(input: ScheduleInput): ResearchSchedule {
  const ts = nowIso();
  return {
    id: crypto.randomUUID(),
    ...input,
    is_active: true,
    last_run: null,
    created_at: ts,
    updated_at: ts,
  };
}

export function updateSchedule(
  schedule: ResearchSchedule,
  patch: Partial<ScheduleInput> & { is_active?: boolean; last_run?: string | null },
): ResearchSchedule {
  return {
    ...schedule,
    ...patch,
    updated_at: nowIso(),
  };
}

