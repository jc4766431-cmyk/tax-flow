"use client";

/**
 * Route protection for everything under (dashboard).
 *
 * Deliberate tradeoff, per HANDOFF.md §3c — flagging rather than silently
 * deciding: this guard is client-side only, checking useCurrentUser() and
 * redirecting to /login on error. lib/api.ts stores tokens in localStorage,
 * which a Next.js middleware.ts can't read, so real middleware-based route
 * protection would require the backend to set an httpOnly cookie on login
 * instead of (or alongside) returning tokens in the JSON body. That's the
 * more secure long-term choice for a fintech-adjacent product handling PAN/
 * GSTIN/financial documents, but it's a backend + frontend change together,
 * not something to do halfway — it hasn't been done this pass. Until then:
 * there's a brief flash where an unauthenticated visitor could see this
 * layout mount before the redirect fires, and there's no server-side
 * enforcement at all (a request to a backend endpoint without a valid token
 * still correctly 401s server-side — this guard is only about the frontend
 * route, not an API security boundary).
 */

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useCurrentUser } from "@/hooks/use-auth";
import { tokenStorage } from "@/lib/api";
import { DashboardChrome } from "@/components/dashboard/dashboard-chrome";
import { Skeleton } from "@/components/ui/skeleton";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const { data: user, isLoading, isError } = useCurrentUser();
  const hasToken = typeof window !== "undefined" && !!tokenStorage.getAccess();

  useEffect(() => {
    if (!hasToken || isError) {
      router.replace("/login");
    }
  }, [hasToken, isError, router]);

  if (!hasToken || isError) {
    return null;
  }

  if (isLoading || !user) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[var(--bg)]">
        <div className="w-full max-w-sm space-y-3 px-6">
          <Skeleton className="h-6 w-2/3" />
          <Skeleton className="h-24 w-full" />
          <Skeleton className="h-24 w-full" />
        </div>
      </div>
    );
  }

  return <DashboardChrome user={user}>{children}</DashboardChrome>;
}
