import { apiFetch } from "@/lib/api";
import { shouldUseMock } from "@/lib/mock-sse";
import { getMockAnalytics, type AnalyticsResponse } from "@/lib/mock-analytics";

export type { AnalyticsResponse } from "@/lib/mock-analytics";

export async function fetchAnalytics(): Promise<AnalyticsResponse> {
  if (shouldUseMock()) return getMockAnalytics();

  try {
    return await apiFetch<AnalyticsResponse>("/api/v1/analytics");
  } catch {
    return getMockAnalytics();
  }
}

