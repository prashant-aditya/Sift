import { createBrowserClient } from "@supabase/ssr";
import { createServerClient } from "@supabase/ssr";
import type { SupabaseClient } from "@supabase/supabase-js";
import type { cookies } from "next/headers";

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL ?? "";
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ?? "";

export function isSupabaseConfigured(): boolean {
  return supabaseUrl.length > 0 && supabaseAnonKey.length > 0;
}

export function createClient(): SupabaseClient | null {
  if (!isSupabaseConfigured()) return null;
  return createBrowserClient(supabaseUrl, supabaseAnonKey);
}

export function createServerSupabaseClient(
  cookieStore: Awaited<ReturnType<typeof cookies>>,
): SupabaseClient | null {
  if (!isSupabaseConfigured()) return null;
  return createServerClient(supabaseUrl, supabaseAnonKey, {
    cookies: {
      getAll() {
        return cookieStore.getAll();
      },
      setAll(cookiesToSet) {
        try {
          cookiesToSet.forEach(({ name, value, options }) =>
            cookieStore.set(name, value, options),
          );
        } catch {
          // setAll can fail in Server Components — safe to ignore
        }
      },
    },
  });
}
