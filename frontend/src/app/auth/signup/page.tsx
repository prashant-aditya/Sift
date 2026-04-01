import { SignupForm } from "@/components/auth/SignupForm";

export const metadata = {
  title: "Sign Up — Sift",
  description: "Create a free Sift account to save and revisit your research.",
};

export default function SignupPage() {
  return (
    <div className="flex min-h-[calc(100dvh-3rem)] items-center justify-center p-4">
      <SignupForm />
    </div>
  );
}
