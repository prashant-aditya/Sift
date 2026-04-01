"use client";

import { Download, FileJson, FileText, Vault } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { apiFetchBlob } from "@/lib/api";

type ExportFormat = "markdown" | "json";

function toSafeFilename(input: string): string {
  return input
    .trim()
    .replace(/[\/\\?%*:|"<>]/g, "-")
    .replace(/\s+/g, " ")
    .slice(0, 120);
}

async function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  try {
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.rel = "noopener";
    document.body.appendChild(a);
    a.click();
    a.remove();
  } finally {
    URL.revokeObjectURL(url);
  }
}

export function ExportMenu({
  sessionId,
  sessionTitle,
}: {
  sessionId: string;
  sessionTitle: string;
}) {
  async function exportSession(format: ExportFormat) {
    const blob = await apiFetchBlob(
      `/api/v1/sessions/${encodeURIComponent(sessionId)}/export?format=${encodeURIComponent(
        format,
      )}`,
      { method: "GET" },
    );

    const base = toSafeFilename(sessionTitle || `session-${sessionId}`);
    const filename = format === "markdown" ? `${base}.md` : `${base}.json`;
    await downloadBlob(blob, filename);
  }

  async function exportObsidian() {
    const blob = await apiFetchBlob(
      `/api/v1/knowledge/export?format=${encodeURIComponent("obsidian")}`,
      { method: "GET" },
    );
    await downloadBlob(blob, "sift-obsidian-vault.zip");
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        render={
          <Button
            variant="outline"
            size="sm"
            className="touch-target"
            aria-label="Export session"
          />
        }
      >
        <Download className="size-4" />
        Export
      </DropdownMenuTrigger>

      <DropdownMenuContent align="end" side="bottom" sideOffset={8}>
        <DropdownMenuLabel>Export</DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuItem
          onClick={() => {
            void exportSession("markdown").catch(() => {});
          }}
        >
          <FileText className="size-4" />
          Export as Markdown
        </DropdownMenuItem>
        <DropdownMenuItem
          onClick={() => {
            void exportSession("json").catch(() => {});
          }}
        >
          <FileJson className="size-4" />
          Export as JSON
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuItem
          onClick={() => {
            void exportObsidian().catch(() => {});
          }}
        >
          <Vault className="size-4" />
          Export to Obsidian
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

