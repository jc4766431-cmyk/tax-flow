"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import {
  Users,
  FileClock,
  AlertTriangle,
  FileSearch,
  CalendarClock,
  ArrowRight,
} from "lucide-react";
import { api } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { StatCard } from "@/components/dashboard/stat-card";
import type { FirmOverview } from "@/lib/types";

function useFirmOverview() {
  return useQuery<FirmOverview>({
    queryKey: ["dashboard", "firm-overview"],
    queryFn: async () => (await api.get("/dashboard/firm-overview")).data,
  });
}

const QUICK_LINKS = [
  {
    href: "/admin/clients",
    title: "Clients",
    description: "Search, browse, and manage every client on your firm's roster.",
  },
  {
    href: "/admin/board",
    title: "Workflow board",
    description: "Move filings through the six-stage pipeline, from new client to filed.",
  },
  {
    href: "/admin/reports",
    title: "Reports",
    description: "Monthly filing volume, staff productivity, and turnaround analytics.",
  },
];

export default function AccountantDashboardPage() {
  const { data, isLoading, isError, error } = useFirmOverview();

  if (isError) throw error;

  if (isLoading || !data) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-1/3" />
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-24 w-full" />
          ))}
        </div>
        <Skeleton className="h-40 w-full" />
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="font-[family-name:var(--font-display)] text-2xl font-semibold text-[var(--ink)]">
          Firm overview
        </h1>
        <p className="mt-1 text-sm text-[var(--ink-muted)]">
          Where every client and filing stands right now.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5">
        <StatCard label="Active clients" value={data.active_clients} icon={Users} />
        <StatCard label="Pending filings" value={data.pending_filings} icon={FileClock} />
        <StatCard
          label="Overdue"
          value={data.overdue_tasks}
          icon={AlertTriangle}
          tone={data.overdue_tasks > 0 ? "overdue" : "neutral"}
        />
        <StatCard
          label="Docs awaiting review"
          value={data.documents_awaiting_review}
          icon={FileSearch}
          tone={data.documents_awaiting_review > 0 ? "brass" : "neutral"}
        />
        <StatCard
          label="Due within 14 days"
          value={data.upcoming_deadlines_14d}
          icon={CalendarClock}
        />
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        {QUICK_LINKS.map((link) => (
          <Link key={link.href} href={link.href}>
            <Card className="h-full transition-colors hover:border-[var(--brass)]/40 hover:bg-[var(--surface-hover)]">
              <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle>{link.title}</CardTitle>
                <ArrowRight size={16} className="text-[var(--ink-muted)]" />
              </CardHeader>
              <CardContent>
                <p className="text-sm text-[var(--ink-muted)]">{link.description}</p>
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
}
