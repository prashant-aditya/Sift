import { z } from "zod";

export const scheduleFrequencySchema = z.enum(["daily", "weekly"]);

export const scheduleInputSchema = z.object({
  query_template: z
    .string()
    .trim()
    .min(1, "Query template is required"),
  topics: z
    .array(z.string().trim().min(1))
    .min(1, "At least one topic is required"),
  frequency: scheduleFrequencySchema,
  sources: z
    .array(z.string().trim().min(1))
    .min(1, "Select at least one source"),
});

export type ScheduleFrequency = z.infer<typeof scheduleFrequencySchema>;
export type ScheduleInput = z.infer<typeof scheduleInputSchema>;

export type ResearchSchedule = ScheduleInput & {
  id: string;
  is_active: boolean;
  last_run: string | null;
  created_at: string;
  updated_at: string;
};

