import { NextResponse, type NextRequest } from "next/server";
import { scheduleInputSchema } from "@/lib/schedules";
import { createSchedule, getScheduleStore } from "./_store";

export async function GET() {
  const { schedules } = getScheduleStore();
  return NextResponse.json(schedules);
}

export async function POST(request: NextRequest) {
  const json = (await request.json().catch(() => null)) as unknown;
  const parsed = scheduleInputSchema.safeParse(json);
  if (!parsed.success) {
    return NextResponse.json(
      { message: "Invalid schedule", issues: parsed.error.issues },
      { status: 400 },
    );
  }

  const store = getScheduleStore();
  const schedule = createSchedule(parsed.data);
  store.schedules.unshift(schedule);

  return NextResponse.json(schedule, { status: 201 });
}

