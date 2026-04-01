 "use client";
 
 import { useEffect, useMemo, useState } from "react";
 import { apiFetch } from "@/lib/api";
 import { SOURCES, SOURCE_MAP, type SourceConfig } from "@/lib/constants";
 import { Globe } from "lucide-react";
 
 type ApiSource = {
   name: string;
   display_name?: string;
   displayName?: string;
 };
 
 function normalizeSourceName(name: string): string {
   const n = name.trim().toLowerCase();
   if (n === "ddg") return "duckduckgo";
   if (n === "hn") return "hackernews";
   if (n === "wiki") return "wikipedia";
   return n;
 }
 
 function genericSourceConfig(name: string, displayName?: string): SourceConfig {
   const label =
     displayName ??
     name
       .split(/[_-]/g)
       .filter(Boolean)
       .map((p) => p.charAt(0).toUpperCase() + p.slice(1))
       .join(" ");
 
   return {
     name,
     displayName: label,
     icon: Globe,
     color: "#64748b",
     bgClass: "bg-slate-500",
     textClass: "text-slate-500",
     borderClass: "border-slate-500",
   };
 }
 
 export function useSources(): {
   sources: SourceConfig[];
   isLoading: boolean;
   error: string | null;
 } {
   const [apiSources, setApiSources] = useState<ApiSource[] | null>(null);
   const [isLoading, setIsLoading] = useState(false);
   const [error, setError] = useState<string | null>(null);
 
   useEffect(() => {
     let cancelled = false;
 
     async function run() {
       setIsLoading(true);
       setError(null);
       try {
         const res = await apiFetch<ApiSource[]>("/api/v1/sources");
         if (cancelled) return;
         setApiSources(Array.isArray(res) ? res : null);
       } catch (e) {
         if (cancelled) return;
         setApiSources(null);
         setError(e instanceof Error ? e.message : "Failed to load sources");
       } finally {
         if (!cancelled) setIsLoading(false);
       }
     }
 
     run();
     return () => {
       cancelled = true;
     };
   }, []);
 
   const sources = useMemo(() => {
     if (!apiSources || apiSources.length === 0) return SOURCES;
 
     const seen = new Set<string>();
     const mapped: SourceConfig[] = [];
 
     for (const s of apiSources) {
       if (!s?.name) continue;
       const normalized = normalizeSourceName(s.name);
       if (seen.has(normalized)) continue;
       seen.add(normalized);
 
       const config = SOURCE_MAP[normalized];
       if (config) {
         mapped.push(config);
       } else {
         mapped.push(
           genericSourceConfig(
             normalized,
             s.displayName ?? s.display_name ?? undefined,
           ),
         );
       }
     }
 
     return mapped.length > 0 ? mapped : SOURCES;
   }, [apiSources]);
 
   return { sources, isLoading, error };
 }
