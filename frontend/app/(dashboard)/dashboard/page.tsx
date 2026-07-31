"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { MessageCircle, FileText, Clock, Inbox, ChevronDown } from "lucide-react";
import { api } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { StatCard } from "@/components/dashboard/stat-card";
import { EmptyState } from "@/components/dashboard/empty-state";
import { FilingTimeline } from "@/components/dashboard/filing-timeline";
import { DocumentChecklist } from "@/components/dashboard/document-checklist";
import { MessageThread } from "@/components/dashboard/message-thread";
import { stageTone } from "@/lib/stage-tone";
import { FILING_STAGES, FILING_TYPE_LABELS, type ClientOverview } from "@/lib/types";

function useClientOverview() {
  return useQuery<ClientOverview>({
    queryKey: ["dashboard", "client-overview"],
    queryFn: async () => (await api.get("/dashboard/client-overview")).data,
  });
}

export default function ClientDashboardPage() {
  const { data, isLoading, isError, error } = useClientOverview();
  const [expandedId, setExpandedId] = useState<string | null>(null);

  // Follows HANDOFF.md §6's pattern: let the nearest error.tsx boundary
  // catch a thrown React Query error rather than hand-rolling an inline
  // error state per page.
  if (isError) throw error;

  if (isLoading || !data) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-1/3" />
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <Skeleton className="h-24 w-full" />
          <Skeleton className="h-24 w-full" />
        </div>
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  const activeFilings = data.filing_status.filter(
    (f) => f.stage !== "filed" && f.stage !== "completed"
  ).length;

  return (
    <div className="space-y-8">
      <div>
        <h1 className="font-[family-name:var(--font-display)] text-2xl font-semibold text-[var(--ink)]">
          Your filings
        </h1>
        <p className="mt-1 text-sm text-[var(--ink-muted)]">
          A record of what your accountant is working on.
        </p>
      </div>

      <Card className="border-[var(--brass)]/25 bg-[var(--brass)]/[0.06]">
        <CardContent className="flex items-start gap-4 p-5">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-[var(--radius-sm)] bg-[var(--brass)]/15 text-[var(--brass)]">
            <MessageCircle size={18} />
          </div>
          <div>
            <p className="text-sm font-medium text-[var(--ink)]">
              Document requests and updates come to you on WhatsApp
            </p>
            <p className="mt-1 text-sm text-[var(--ink-muted)]">
              Your accountant sends checklists and reminders straight to your
              phone — no login needed. This page is here for whenever you
              want to browse the full history yourself.
            </p>
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <StatCard label="Active filings" value={activeFilings} icon={FileText} />
        <StatCard
          label="Documents pending"
          value={data.pending_uploads}
          icon={Inbox}
          tone={data.pending_uploads > 0 ? "brass" : "neutral"}
        />
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Filing status</CardTitle>
        </CardHeader>
        <CardContent>
          {data.filing_status.length === 0 ? (
            <EmptyState
              icon={FileText}
              title="No filings yet"
              description="Once your accountant starts a filing on your behalf, it'll show up here with its current stage."
            />
          ) : (
            <ul className="divide-y divide-[var(--line)]">
              {data.filing_status.map((filing) => {
                const stageLabel =
                  FILING_STAGES.find((s) => s.key === filing.stage)?.label ??
                  filing.stage;
                const overdue =
                  filing.due_date &&
                  filing.stage !== "filed" &&
                  filing.stage !== "completed" &&
                  new Date(filing.due_date) < new Date();

                const isExpanded = expandedId === filing.id;

                return (
                  <li key={filing.id} className="py-4 first:pt-0 last:pb-0">
                    <button
                      type="button"
                      onClick={() => setExpandedId(isExpanded ? null : filing.id)}
                      className="flex w-full flex-wrap items-center justify-between gap-3 text-left"
                      aria-expanded={isExpanded}
                    >
                      <div>
                        <p className="text-sm font-medium text-[var(--ink)]">
                          {FILING_TYPE_LABELS[filing.type]}
                        </p>
                        {filing.due_date && (
                          <p className="tabular mt-0.5 text-xs text-[var(--ink-muted)]">
                            Due {new Date(filing.due_date).toLocaleDateString("en-IN")}
                          </p>
                        )}
                      </div>
                      <div className="flex items-center gap-2">
                        {overdue && (
                          <Badge tone="overdue">
                            <Clock size={12} /> Overdue
                          </Badge>
                        )}
                        <Badge tone={stageTone(filing.stage)}>{stageLabel}</Badge>
                        <ChevronDown
                          size={16}
                          className={`text-[var(--ink-muted)] transition-transform ${
                            isExpanded ? "rotate-180" : ""
                          }`}
                        />
                      </div>
                    </button>
                    {isExpanded && (
                      <>
                        <FilingTimeline filingId={filing.id} />
                        <DocumentChecklist
                          filingId={filing.id}
                          clientId={data.client_id}
                        />
                      </>
                    )}
                  </li>
                );
              })}
            </ul>
          )}
        </CardContent>
      </Card>

      <MessageThread clientId={data.client_id} recipientId={data.assigned_accountant_id} />
    </div>
  );
}
