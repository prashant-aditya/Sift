import { Suspense } from "react";
import { LoginForm } from "@/components/auth/LoginForm";
import { Skeleton } from "@/components/ui/skeleton";

export const metadata = {
  title: "Sign In — Sift",
  description: "Sign in to your Sift account to access your research sessions.",
};

function LoginFormFallback() {
  return (
    <div className="w-full max-w-md space-y-4 rounded-xl border border-border p-6">
      <Skeleton className="mx-auto h-8 w-48" />
      <Skeleton className="mx-auto h-4 w-64" />
      <Skeleton className="h-10 w-full" />
      <Skeleton className="h-10 w-full" />
      <Skeleton className="h-10 w-full" />
    </div>
  );
}

export default function LoginPage() {
  return (
    <div className="flex min-h-[calc(100dvh-3rem)] items-center justify-center p-4">
      <Suspense fallback={<LoginFormFallback />}>
        <LoginForm />
      </Suspense>
    </div>
  );
}
