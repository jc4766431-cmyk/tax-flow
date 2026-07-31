"use client";

import { useQuery } from "@tanstack/react-query";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import Link from "next/link";
import { api } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { StatCard } from "@/components/dashboard/stat-card";
import { FileCheck2, Clock, TrendingUp, IndianRupee } from "lucide-react";

interface ReportsSummary {
  period_start: string;
  period_end: string;
  monthly_filings: { month: string; count: number }[];
  revenue: number;
  staff_productivity: { accountant_id: string; accountant_name: string; filings_completed: number }[];
  turnaround: { avg_days: number | null; sample_size: number };
  completion_rate: number;
}

function useReportsSummary() {
  return useQuery<ReportsSummary>({
    queryKey: ["reports", "summary"],
    queryFn: async () => (await api.get("/reports/summary")).data,
  });
}

export default function ReportsPage() {
  const { data, isLoading, isError, error } = useReportsSummary();

  if (isError) throw error;

  if (isLoading || !data) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-1/3" />
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-24 w-full" />
          ))}
        </div>
        <Skeleton className="h-72 w-full" />
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="font-[family-name:var(--font-display)] text-2xl text-[var(--ink)]">
          Reports
        </h1>
        <p className="tabular mt-1 text-sm text-[var(--ink-muted)]">
          {data.period_start} &ndash; {data.period_end}
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-4">
        <Link href="/admin/invoices" className="block transition-opacity hover:opacity-90">
          <StatCard
            label="Revenue (paid invoices)"
            value={`₹${data.revenue.toLocaleString("en-IN")}`}
            icon={IndianRupee}
            tone="brass"
          />
        </Link>
        <StatCard
          label="Completion rate"
          value={`${Math.round(data.completion_rate * 100)}%`}
          icon={FileCheck2}
        />
        <StatCard
          label="Avg. turnaround (days)"
          value={data.turnaround.avg_days != null ? data.turnaround.avg_days.toFixed(1) : "—"}
          icon={Clock}
        />
        <StatCard
          label="Filings this period"
          value={data.monthly_filings.reduce((sum, m) => sum + m.count, 0)}
          icon={TrendingUp}
        />
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Filings per month</CardTitle>
        </CardHeader>
        <CardContent className="h-72">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data.monthly_filings}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--line)" />
              <XAxis dataKey="month" stroke="var(--ink-muted)" fontSize={12} />
              <YAxis allowDecimals={false} stroke="var(--ink-muted)" fontSize={12} />
              <Tooltip
                contentStyle={{
                  background: "var(--surface)",
                  border: "1px solid var(--line)",
                  borderRadius: "var(--radius-sm)",
                  color: "var(--ink)",
                }}
              />
              <Bar dataKey="count" fill="var(--brass)" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Staff productivity</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {data.staff_productivity.length === 0 ? (
            <p className="p-5 text-sm text-[var(--ink-muted)]">
              No completed filings in this period yet.
            </p>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-t border-[var(--line)] text-left text-xs uppercase tracking-wide text-[var(--ink-muted)]">
                  <th className="px-5 py-3 font-medium">Accountant</th>
                  <th className="px-5 py-3 font-medium">Filings completed</th>
                </tr>
              </thead>
              <tbody>
                {data.staff_productivity.map((row) => (
                  <tr key={row.accountant_id} className="border-t border-[var(--line)]">
                    <td className="px-5 py-3 text-[var(--ink)]">{row.accountant_name}</td>
                    <td className="tabular px-5 py-3 text-[var(--ink)]">{row.filings_completed}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </CardContent>
      </Card>

    </div>
  );
}
