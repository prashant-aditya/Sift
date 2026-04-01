"use client";

import dynamic from "next/dynamic";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { SourcePerformance } from "@/components/dashboard/SourcePerformance";
import { CacheStats } from "@/components/dashboard/CacheStats";
import { TopEntities } from "@/components/dashboard/TopEntities";
import { KnowledgeStats } from "@/components/dashboard/KnowledgeStats";
import { useAnalytics } from "@/hooks/useAnalytics";

const ActivityChart = dynamic(
  () =>
    import("@/components/dashboard/ActivityChart").then((m) => m.ActivityChart),
  { ssr: false, loading: () => <div className="h-64 w-full animate-pulse rounded-md bg-muted" /> },
);

function SkeletonCard({ title, heightClass }: { title: string; heightClass: string }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <div className={["w-full animate-pulse rounded-md bg-muted", heightClass].join(" ")} />
      </CardContent>
    </Card>
  );
}

export default function DashboardPage() {
  const { status, data, error, reload } = useAnalytics();

  if (status === "loading" || status === "idle") {
    return (
      <main className="mx-auto w-full max-w-6xl px-4 py-6">
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <SkeletonCard title="Research activity" heightClass="h-64" />
          <SkeletonCard title="Source performance" heightClass="h-64" />
          <SkeletonCard title="Cache stats" heightClass="h-64" />
          <SkeletonCard title="Top entities" heightClass="h-64" />
          <SkeletonCard title="Knowledge stats" heightClass="h-64" />
        </div>
      </main>
    );
  }

  if (status === "error") {
    return (
      <main className="mx-auto w-full max-w-6xl px-4 py-6">
        <Card>
          <CardHeader>
            <CardTitle>Dashboard</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <p className="text-sm text-muted-foreground">
                {error ?? "Failed to load analytics."}
              </p>
              <button
                type="button"
                className="text-sm font-medium text-primary underline-offset-4 hover:underline"
                onClick={() => void reload()}
              >
                Retry
              </button>
            </div>
          </CardContent>
        </Card>
      </main>
    );
  }

  if (status !== "success" || !data) {
    return null;
  }

  return (
    <main className="mx-auto w-full max-w-6xl px-4 py-6">
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Research activity</CardTitle>
          </CardHeader>
          <CardContent>
            <ActivityChart data={data.research_by_week} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Source performance</CardTitle>
          </CardHeader>
          <CardContent>
            <SourcePerformance data={data.source_performance} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Cache stats</CardTitle>
          </CardHeader>
          <CardContent>
            <CacheStats data={data.cache_stats} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Top entities</CardTitle>
          </CardHeader>
          <CardContent>
            <TopEntities data={data.top_entities} />
          </CardContent>
        </Card>

        <Card className="md:col-span-2">
          <CardHeader>
            <CardTitle>Knowledge stats</CardTitle>
          </CardHeader>
          <CardContent>
            <KnowledgeStats
              totalSessions={data.total_sessions}
              graph={data.knowledge_graph_stats}
              byWeek={data.knowledge_by_week}
            />
          </CardContent>
        </Card>
      </div>
    </main>
  );
}

