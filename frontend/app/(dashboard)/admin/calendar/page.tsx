"use client";

import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ChevronLeft, ChevronRight, CalendarDays } from "lucide-react";
import { api } from "@/lib/api";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/dashboard/empty-state";
import { useClientsList } from "@/hooks/use-clients";
import { FILING_TYPE_LABELS, type FilingRequest } from "@/lib/types";
import { cn } from "@/lib/utils";

const WEEKDAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

function useFilings() {
  return useQuery<FilingRequest[]>({
    queryKey: ["filings", "all"],
    queryFn: async () => (await api.get("/filings")).data,
  });
}

function isSameDay(a: Date, b: Date) {
  return (
    a.getFullYear() === b.getFullYear() &&
    a.getMonth() === b.getMonth() &&
    a.getDate() === b.getDate()
  );
}

function buildMonthGrid(year: number, month: number): Date[] {
  const firstOfMonth = new Date(year, month, 1);
  const startOffset = firstOfMonth.getDay();
  const gridStart = new Date(year, month, 1 - startOffset);
  return Array.from({ length: 42 }, (_, i) => {
    const d = new Date(gridStart);
    d.setDate(gridStart.getDate() + i);
    return d;
  });
}

function stageTone(stage: FilingRequest["stage"]) {
  if (stage === "filed" || stage === "completed") return "verified" as const;
  if (stage === "approval_required") return "pending" as const;
  return "neutral" as const;
}

export default function CalendarPage() {
  const today = useMemo(() => new Date(), []);
  const [cursor, setCursor] = useState(() => new Date(today.getFullYear(), today.getMonth(), 1));
  const { data: filings, isLoading, isError, error } = useFilings();
  const { data: clientsPage } = useClientsList();
  const clients = clientsPage?.items ?? [];
  const clientName = (id: string) =>
    clients.find((c) => c.id === id)?.company_name ?? id.slice(0, 8);

  if (isError) throw error;

  const withDueDates = (filings ?? []).filter((f) => !!f.due_date);
  const days = buildMonthGrid(cursor.getFullYear(), cursor.getMonth());

  const byDay = new Map<string, FilingRequest[]>();
  for (const f of withDueDates) {
    const d = new Date(f.due_date as string);
    const key = `${d.getFullYear()}-${d.getMonth()}-${d.getDate()}`;
    byDay.set(key, [...(byDay.get(key) ?? []), f]);
  }

  const monthLabel = cursor.toLocaleDateString("en-IN", { month: "long", year: "numeric" });

  const upcoming = withDueDates
    .filter((f) => f.stage !== "filed" && f.stage !== "completed")
    .sort(
      (a, b) => new Date(a.due_date as string).getTime() - new Date(b.due_date as string).getTime()
    )
    .slice(0, 6);

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="font-[family-name:var(--font-display)] text-2xl font-semibold text-[var(--ink)]">
            Calendar
          </h1>
          <p className="mt-1 text-sm text-[var(--ink-muted)]">
            Filing deadlines across all your clients.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setCursor((c) => new Date(c.getFullYear(), c.getMonth() - 1, 1))}
          >
            <ChevronLeft size={14} />
          </Button>
          <span className="min-w-36 text-center text-sm font-medium text-[var(--ink)]">
            {monthLabel}
          </span>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setCursor((c) => new Date(c.getFullYear(), c.getMonth() + 1, 1))}
          >
            <ChevronRight size={14} />
          </Button>
        </div>
      </div>

      {isLoading || !filings ? (
        <Skeleton className="h-[32rem] w-full" />
      ) : withDueDates.length === 0 ? (
        <EmptyState
          icon={CalendarDays}
          title="No deadlines yet"
          description="Filings with a due date will appear here on their scheduled day."
        />
      ) : (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-[1fr_18rem]">
          <Card>
            <CardContent className="p-3">
              <div className="grid grid-cols-7 gap-px overflow-hidden rounded-[var(--radius-sm)] bg-[var(--line)]">
                {WEEKDAYS.map((w) => (
                  <div
                    key={w}
                    className="bg-[var(--bg-elevated)] px-2 py-1.5 text-center text-xs font-medium uppercase tracking-wide text-[var(--ink-muted)]"
                  >
                    {w}
                  </div>
                ))}
                {days.map((d, i) => {
                  const key = `${d.getFullYear()}-${d.getMonth()}-${d.getDate()}`;
                  const events = byDay.get(key) ?? [];
                  const inMonth = d.getMonth() === cursor.getMonth();
                  const isToday = isSameDay(d, today);
                  return (
                    <div
                      key={i}
                      className={cn(
                        "min-h-24 bg-[var(--bg-elevated)] p-1.5 align-top",
                        !inMonth && "opacity-40"
                      )}
                    >
                      <span
                        className={cn(
                          "tabular inline-flex h-5 w-5 items-center justify-center rounded-full text-xs",
                          isToday ? "bg-[var(--brass)] text-[#17233A]" : "text-[var(--ink-muted)]"
                        )}
                      >
                        {d.getDate()}
                      </span>
                      <div className="mt-1 space-y-1">
                        {events.slice(0, 3).map((f) => (
                          <div
                            key={f.id}
                            title={`${clientName(f.client_id)} — ${FILING_TYPE_LABELS[f.filing_type]}`}
                            className="truncate rounded-[4px] bg-[var(--pending-bg)] px-1.5 py-0.5 text-[11px] text-[var(--pending)]"
                          >
                            {clientName(f.client_id)}
                          </div>
                        ))}
                        {events.length > 3 && (
                          <p className="text-[10px] text-[var(--ink-faint)]">
                            +{events.length - 3} more
                          </p>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="space-y-3 p-5">
              <h2 className="text-xs font-medium uppercase tracking-wide text-[var(--ink-muted)]">
                Upcoming deadlines
              </h2>
              {upcoming.length === 0 ? (
                <p className="text-sm text-[var(--ink-muted)]">Nothing due soon.</p>
              ) : (
                <ul className="space-y-3">
                  {upcoming.map((f) => (
                    <li key={f.id} className="flex items-start justify-between gap-2 text-sm">
                      <div>
                        <p className="font-medium text-[var(--ink)]">{clientName(f.client_id)}</p>
                        <p className="text-xs text-[var(--ink-muted)]">
                          {FILING_TYPE_LABELS[f.filing_type]}
                        </p>
                      </div>
                      <div className="text-right">
                        <p className="tabular text-xs text-[var(--ink-muted)]">
                          {new Date(f.due_date as string).toLocaleDateString("en-IN", {
                            day: "numeric",
                            month: "short",
                          })}
                        </p>
                        <Badge tone={stageTone(f.stage)} className="mt-1">
                          {f.stage.replace(/_/g, " ")}
                        </Badge>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
