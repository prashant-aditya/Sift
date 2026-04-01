"use client";

import * as React from "react";
import { fetchAnalytics, type AnalyticsResponse } from "@/lib/analytics";

type State =
  | { status: "idle" | "loading"; data: null; error: null }
  | { status: "success"; data: AnalyticsResponse; error: null }
  | { status: "error"; data: null; error: string };

export function useAnalytics() {
  const [state, setState] = React.useState<State>({
    status: "idle",
    data: null,
    error: null,
  });

  const load = React.useCallback(async () => {
    setState({ status: "loading", data: null, error: null });
    try {
      const data = await fetchAnalytics();
      setState({ status: "success", data, error: null });
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Failed to load analytics";
      setState({ status: "error", data: null, error: msg });
    }
  }, []);

  React.useEffect(() => {
    void load();
  }, [load]);

  return { ...state, reload: load };
}

