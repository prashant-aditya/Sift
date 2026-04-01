"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import type { User, AuthError } from "@supabase/supabase-js";
import { createClient, isSupabaseConfigured } from "@/lib/supabase";

interface UseAuthReturn {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  isConfigured: boolean;
  signIn: (email: string, password: string) => Promise<{ error: AuthError | null }>;
  signUp: (email: string, password: string) => Promise<{ error: AuthError | null }>;
  signInWithGitHub: () => Promise<{ error: AuthError | null }>;
  signOut: () => Promise<void>;
}

const NOT_CONFIGURED_ERROR = {
  message: "Supabase is not configured. Set NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY.",
  name: "AuthError",
  status: 0,
} as AuthError;

export function useAuth(): UseAuthReturn {
  const [user, setUser] = useState<User | null>(null);
  const configured = isSupabaseConfigured();

  const supabase = useMemo(() => createClient(), []);
  const [isLoading, setIsLoading] = useState(() => !!supabase);

  useEffect(() => {
    if (!supabase) {
      return;
    }

    supabase.auth.getUser().then(({ data }) => {
      setUser(data.user);
      setIsLoading(false);
    });

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      setUser(session?.user ?? null);
    });

    return () => subscription.unsubscribe();
  }, [supabase]);

  const signIn = useCallback(
    async (email: string, password: string) => {
      if (!supabase) return { error: NOT_CONFIGURED_ERROR };
      const { error } = await supabase.auth.signInWithPassword({
        email,
        password,
      });
      return { error };
    },
    [supabase],
  );

  const signUp = useCallback(
    async (email: string, password: string) => {
      if (!supabase) return { error: NOT_CONFIGURED_ERROR };
      const { error } = await supabase.auth.signUp({
        email,
        password,
        options: {
          emailRedirectTo: `${window.location.origin}/auth/callback`,
        },
      });
      return { error };
    },
    [supabase],
  );

  const signInWithGitHub = useCallback(async () => {
    if (!supabase) return { error: NOT_CONFIGURED_ERROR };
    const { error } = await supabase.auth.signInWithOAuth({
      provider: "github",
      options: {
        redirectTo: `${window.location.origin}/auth/callback`,
      },
    });
    return { error };
  }, [supabase]);

  const signOut = useCallback(async () => {
    if (!supabase) return;
    await supabase.auth.signOut();
    setUser(null);
  }, [supabase]);

  return {
    user,
    isLoading,
    isAuthenticated: !!user,
    isConfigured: configured,
    signIn,
    signUp,
    signInWithGitHub,
    signOut,
  };
}
