"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { LogIn, BookmarkPlus } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogTrigger,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";

export function SignInToSave() {
  const router = useRouter();
  const [open, setOpen] = useState(false);

  function handleSignIn() {
    const redirect = encodeURIComponent(window.location.pathname);
    router.push(`/auth/login?redirect=${redirect}`);
    setOpen(false);
  }

  function handleSignUp() {
    const redirect = encodeURIComponent(window.location.pathname);
    router.push(`/auth/signup?redirect=${redirect}`);
    setOpen(false);
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger
        render={
          <Button variant="outline" size="sm" className="gap-2">
            <BookmarkPlus className="size-4" />
            Save this session
          </Button>
        }
      />
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Sign in to save your research</DialogTitle>
          <DialogDescription>
            Create an account or sign in to save this session, access it later,
            ask follow-up questions, and build your knowledge graph.
          </DialogDescription>
        </DialogHeader>
        <DialogFooter className="flex-col gap-2 sm:flex-row">
          <Button variant="outline" onClick={handleSignUp}>
            Create account
          </Button>
          <Button onClick={handleSignIn} className="gap-2">
            <LogIn className="size-4" />
            Sign in
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
