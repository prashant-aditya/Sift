import { type NextRequest, NextResponse } from "next/server";

const PROTECTED_PREFIXES = ["/session", "/knowledge", "/dashboard", "/settings"];

function isProtectedRoute(pathname: string): boolean {
  return PROTECTED_PREFIXES.some(
    (prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`),
  );
}

function hasSupabaseSession(request: NextRequest): boolean {
  const cookies = request.cookies.getAll();
  return cookies.some(
    (cookie) =>
      cookie.name.startsWith("sb-") && cookie.name.includes("-auth-token"),
  );
}

function isSharedSessionView(request: NextRequest): boolean {
  const { pathname, searchParams } = request.nextUrl;
  if (!(pathname === "/session" || pathname.startsWith("/session/"))) return false;
  return searchParams.has("share");
}

export function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;

  if (!isProtectedRoute(pathname)) {
    return NextResponse.next();
  }

  if (isSharedSessionView(request)) {
    return NextResponse.next();
  }

  if (hasSupabaseSession(request)) {
    return NextResponse.next();
  }

  const loginUrl = new URL("/auth/login", request.url);
  loginUrl.searchParams.set("redirect", pathname);

  return NextResponse.redirect(loginUrl);
}

export const config = {
  matcher: [
    "/session/:path*",
    "/knowledge/:path*",
    "/dashboard/:path*",
    "/settings/:path*",
  ],
};

