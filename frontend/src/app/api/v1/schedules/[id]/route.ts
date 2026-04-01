import { NextResponse, type NextRequest } from "next/server";
import { scheduleInputSchema } from "@/lib/schedules";
import { z } from "zod";
import { getScheduleStore, updateSchedule } from "../_store";

function notFound() {
  return NextResponse.json({ message: "Schedule not found" }, { status: 404 });
}

export async function PATCH(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  const json = (await request.json().catch(() => null)) as unknown;

  const store = getScheduleStore();
  const idx = store.schedules.findIndex((s) => s.id === id);
  if (idx === -1) return notFound();

  const patchSchema = scheduleInputSchema
    .partial()
    .extend({ is_active: z.boolean().optional() })
    .strict();

  const parsed = patchSchema.safeParse(json);
  if (!parsed.success) {
    return NextResponse.json(
      { message: "Invalid patch", issues: parsed.error.issues },
      { status: 400 },
    );
  }

  const updated = updateSchedule(store.schedules[idx], {
    ...parsed.data,
  });
  store.schedules[idx] = updated;
  return NextResponse.json(updated);
}

export async function DELETE(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  const store = getScheduleStore();
  const before = store.schedules.length;
  store.schedules = store.schedules.filter((s) => s.id !== id);
  if (store.schedules.length === before) return notFound();
  return NextResponse.json({ ok: true });
}

