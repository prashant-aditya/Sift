import type { LucideIcon } from "lucide-react";
import {
  Globe,
  MessageCircle,
  Flame,
  GraduationCap,
  BookOpen,
} from "lucide-react";

export interface SourceConfig {
  name: string;
  displayName: string;
  icon: LucideIcon;
  color: string;
  bgClass: string;
  textClass: string;
  borderClass: string;
}

export const SOURCES: SourceConfig[] = [
  {
    name: "ddg",
    displayName: "DuckDuckGo",
    icon: Globe,
    color: "#f97316",
    bgClass: "bg-orange-500",
    textClass: "text-orange-500",
    borderClass: "border-orange-500",
  },
  {
    name: "reddit",
    displayName: "Reddit",
    icon: MessageCircle,
    color: "#ef4444",
    bgClass: "bg-red-500",
    textClass: "text-red-500",
    borderClass: "border-red-500",
  },
  {
    name: "hackernews",
    displayName: "HackerNews",
    icon: Flame,
    color: "#d97706",
    bgClass: "bg-amber-600",
    textClass: "text-amber-600",
    borderClass: "border-amber-600",
  },
  {
    name: "arxiv",
    displayName: "ArXiv",
    icon: GraduationCap,
    color: "#2563eb",
    bgClass: "bg-blue-600",
    textClass: "text-blue-600",
    borderClass: "border-blue-600",
  },
  {
    name: "wikipedia",
    displayName: "Wikipedia",
    icon: BookOpen,
    color: "#475569",
    bgClass: "bg-slate-600",
    textClass: "text-slate-600",
    borderClass: "border-slate-600",
  },
];

export const SOURCE_MAP = Object.fromEntries(
  SOURCES.map((s) => [s.name, s]),
) as Record<string, SourceConfig>;

export const ENTITY_TYPE_COLORS: Record<
  string,
  { color: string; bgClass: string; textClass: string }
> = {
  technology: {
    color: "#3b82f6",
    bgClass: "bg-blue-500",
    textClass: "text-blue-500",
  },
  concept: {
    color: "#a855f7",
    bgClass: "bg-purple-500",
    textClass: "text-purple-500",
  },
  organization: {
    color: "#22c55e",
    bgClass: "bg-green-500",
    textClass: "text-green-500",
  },
  person: {
    color: "#f97316",
    bgClass: "bg-orange-500",
    textClass: "text-orange-500",
  },
  pattern: {
    color: "#14b8a6",
    bgClass: "bg-teal-500",
    textClass: "text-teal-500",
  },
  algorithm: {
    color: "#ef4444",
    bgClass: "bg-red-500",
    textClass: "text-red-500",
  },
  protocol: {
    color: "#06b6d4",
    bgClass: "bg-cyan-500",
    textClass: "text-cyan-500",
  },
  library: {
    color: "#ec4899",
    bgClass: "bg-pink-500",
    textClass: "text-pink-500",
  },
  service: {
    color: "#10b981",
    bgClass: "bg-emerald-500",
    textClass: "text-emerald-500",
  },
};

export const ROUTES = {
  home: "/",
  session: (id: string) => `/session/${id}`,
  knowledge: "/knowledge",
  dashboard: "/dashboard",
  settings: "/settings",
  schedules: "/settings/schedules",
  login: "/auth/login",
  signup: "/auth/signup",
} as const;

export const RESEARCH_DEPTHS = ["quick", "standard", "deep"] as const;
