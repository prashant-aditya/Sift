"use client";

import { useEffect, useMemo, useState } from "react";
import { Copy, Link2, Share2, Users } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { Avatar, AvatarFallback, AvatarGroup, AvatarImage } from "@/components/ui/avatar";
import { apiFetch, ApiError } from "@/lib/api";

type ShareRole = "viewer" | "editor";

export type Collaborator = {
  id: string;
  email?: string | null;
  name?: string | null;
  avatar_url?: string | null;
  role?: ShareRole | null;
};

type ShareResponse = {
  url?: string;
  token?: string;
  collaborators?: Collaborator[];
};

function initialsFor(nameOrEmail?: string | null): string {
  const raw = (nameOrEmail ?? "").trim();
  if (!raw) return "U";
  const parts = raw.split(/\s+/).filter(Boolean);
  if (parts.length >= 2) return `${parts[0][0]}${parts[1][0]}`.toUpperCase();
  const left = raw.includes("@") ? raw.split("@")[0] : raw;
  return left.slice(0, 2).toUpperCase();
}

export function ShareDialog({
  sessionId,
  sessionTitle,
  onCollaboratorsChange,
}: {
  sessionId: string;
  sessionTitle: string;
  onCollaboratorsChange?: (collaborators: Collaborator[]) => void;
}) {
  const [open, setOpen] = useState(false);
  const [role, setRole] = useState<ShareRole>("viewer");
  const [isGenerating, setIsGenerating] = useState(false);
  const [shareUrl, setShareUrl] = useState<string>("");
  const [error, setError] = useState<string>("");
  const [collaborators, setCollaborators] = useState<Collaborator[]>([]);

  const title = useMemo(
    () => sessionTitle?.trim() || `Session ${sessionId}`,
    [sessionId, sessionTitle],
  );

  useEffect(() => {
    if (!open) return;
    setError("");
    (async () => {
      try {
        const data = await apiFetch<{ collaborators: Collaborator[] }>(
          `/api/v1/sessions/${encodeURIComponent(sessionId)}/collaborators`,
        );
        setCollaborators(data.collaborators ?? []);
        onCollaboratorsChange?.(data.collaborators ?? []);
      } catch {
        // Endpoint may not exist yet; don't block the dialog.
      }
    })();
  }, [open, onCollaboratorsChange, sessionId]);

  async function generateLink() {
    setIsGenerating(true);
    setError("");
    try {
      const res = await apiFetch<ShareResponse>(
        `/api/v1/sessions/${encodeURIComponent(sessionId)}/share`,
        {
          method: "POST",
          body: JSON.stringify({ role }),
        },
      );

      const urlFromApi = res.url?.trim();
      const token = res.token?.trim();

      const fallback =
        typeof window !== "undefined"
          ? `${window.location.origin}/session/${encodeURIComponent(sessionId)}${
              token ? `?share=${encodeURIComponent(token)}` : ""
            }`
          : "";

      const nextUrl = urlFromApi || fallback;
      setShareUrl(nextUrl);

      const nextCollaborators = res.collaborators ?? collaborators;
      if (res.collaborators) {
        setCollaborators(nextCollaborators);
        onCollaboratorsChange?.(nextCollaborators);
      }
    } catch (e) {
      if (e instanceof ApiError) {
        const msg =
          typeof e.body === "object" && e.body && "message" in e.body
            ? String((e.body as { message?: unknown }).message ?? "Failed")
            : "Failed to generate link";
        setError(msg);
      } else {
        setError("Failed to generate link");
      }
    } finally {
      setIsGenerating(false);
    }
  }

  async function copyLink() {
    setError("");
    try {
      await navigator.clipboard.writeText(shareUrl);
    } catch {
      setError("Couldn't copy to clipboard. Please copy the link manually.");
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger
        render={
          <Button
            variant="outline"
            size="sm"
            className="touch-target"
            aria-label="Share session"
          />
        }
      >
        <Share2 className="size-4" />
        Share
      </DialogTrigger>

      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Users className="size-4 text-muted-foreground" aria-hidden="true" />
            Share “{title}”
          </DialogTitle>
          <DialogDescription>
            Generate a shareable link for this session. Viewers can read; editors
            can add follow-up queries.
          </DialogDescription>
        </DialogHeader>

        {collaborators.length > 0 && (
          <div className="flex items-center justify-between gap-3 rounded-lg border bg-muted/30 px-3 py-2">
            <div className="text-xs text-muted-foreground">Collaborators</div>
            <AvatarGroup>
              {collaborators.slice(0, 3).map((c) => {
                const label = c.name || c.email || c.id;
                return (
                  <Avatar key={c.id} size="sm" aria-label={label}>
                    {c.avatar_url ? (
                      <AvatarImage src={c.avatar_url} alt={label} />
                    ) : null}
                    <AvatarFallback>{initialsFor(label)}</AvatarFallback>
                  </Avatar>
                );
              })}
              {collaborators.length > 3 && (
                <div className="text-xs text-muted-foreground">
                  +{collaborators.length - 3}
                </div>
              )}
            </AvatarGroup>
          </div>
        )}

        <div className="space-y-2">
          <div className="text-xs font-medium text-muted-foreground">
            Access level
          </div>
          <Select value={role} onValueChange={(v) => setRole(v as ShareRole)}>
            <SelectTrigger className="w-full">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="viewer">Viewer</SelectItem>
              <SelectItem value="editor">Editor</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-2">
          <div className="text-xs font-medium text-muted-foreground">Link</div>
          <div className="flex gap-2">
            <Input
              value={shareUrl}
              placeholder="Generate a link to share"
              readOnly
              aria-label="Share link"
            />
            <Button
              type="button"
              variant="outline"
              size="icon"
              onClick={copyLink}
              disabled={!shareUrl}
              aria-label="Copy link"
              className="touch-target"
            >
              <Copy className="size-4" />
            </Button>
          </div>
          {error && <p className="text-xs text-destructive">{error}</p>}
        </div>

        <DialogFooter>
          <Button
            type="button"
            onClick={generateLink}
            disabled={isGenerating}
          >
            <Link2 className="size-4" />
            {isGenerating ? "Generating..." : "Generate Link"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

