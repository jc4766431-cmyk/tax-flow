"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { AxiosError } from "axios";
import { AlertTriangle, BellRing, BellOff, ChevronDown, ChevronUp } from "lucide-react";
import { api } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/dashboard/empty-state";
import { DOCUMENT_CATEGORY_LABELS, type DocumentCategory, type EscalationStatus, type Reminder, type ReminderChannel } from "@/lib/types";

function errorMessage(err: unknown, fallback: string) {
  if (err instanceof AxiosError) {
    const detail = err.response?.data?.detail;
    if (typeof detail === "string") return detail;
  }
  return fallback;
}

function useEscalations() {
  return useQuery<EscalationStatus[]>({
    queryKey: ["automation", "escalations"],
    queryFn: async () => (await api.get("/automation/escalations")).data,
  });
}

function useReminders(filingRequestId: string, enabled: boolean) {
  return useQuery<Reminder[]>({
    queryKey: ["automation", "reminders", filingRequestId],
    queryFn: async () =>
      (await api.get("/automation/reminders", { params: { filing_request_id: filingRequestId } })).data,
    enabled,
  });
}

function ReminderRow({ row }: { row: EscalationStatus }) {
  const [expanded, setExpanded] = useState(false);
  const [daysBefore, setDaysBefore] = useState("0");
  const [channel, setChannel] = useState<ReminderChannel>("email");
  const queryClient = useQueryClient();

  const { data: reminders, isLoading } = useReminders(row.filing_request_id, expanded);

  const createReminder = useMutation({
    mutationFn: async () =>
      (
        await api.post("/automation/reminders", {
          filing_request_id: row.filing_request_id,
          days_before_deadline: Number(daysBefore) || 0,
          channel,
        })
      ).data,
    onSuccess: () => {
      toast.success("Reminder scheduled");
      queryClient.invalidateQueries({ queryKey: ["automation", "reminders", row.filing_request_id] });
    },
    onError: (err) => toast.error(errorMessage(err, "Couldn't schedule that reminder.")),
  });

  const cancelReminder = useMutation({
    mutationFn: async (id: string) => (await api.patch(`/automation/reminders/${id}/cancel`)).data,
    onSuccess: () => {
      toast.success("Reminder cancelled");
      queryClient.invalidateQueries({ queryKey: ["automation", "reminders", row.filing_request_id] });
    },
    onError: (err) => toast.error(errorMessage(err, "Couldn't cancel that reminder.")),
  });

  return (
    <>
      <tr className="border-t border-[var(--line)]">
        <td className="px-5 py-3 text-[var(--ink)]">{row.client_name}</td>
        <td className="px-5 py-3">
          <div className="flex flex-wrap gap-1">
            {row.missing_categories.map((cat, i) => (
              <Badge key={i} tone="overdue">
                {DOCUMENT_CATEGORY_LABELS[cat as DocumentCategory] ?? cat}
              </Badge>
            ))}
          </div>
        </td>
        <td className="tabular px-5 py-3 text-[var(--ink-muted)]">{row.due_date ?? "—"}</td>
        <td className="tabular px-5 py-3 text-[var(--overdue)]">{row.days_overdue}d overdue</td>
        <td className="tabular px-5 py-3 text-[var(--ink-muted)]">{row.follow_ups_sent}</td>
        <td className="px-5 py-3 text-right">
          <Button size="sm" variant="ghost" onClick={() => setExpanded((v) => !v)}>
            Reminders
            {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          </Button>
        </td>
      </tr>
      {expanded && (
        <tr className="border-t border-[var(--line)] bg-[var(--bg)]">
          <td colSpan={6} className="px-5 py-4">
            <div className="space-y-3">
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  createReminder.mutate();
                }}
                className="flex flex-wrap items-end gap-3"
              >
                <div>
                  <Label htmlFor={`days-${row.filing_request_id}`}>Days before deadline</Label>
                  <Input
                    id={`days-${row.filing_request_id}`}
                    inputMode="numeric"
                    className="w-32"
                    value={daysBefore}
                    onChange={(e) => setDaysBefore(e.target.value)}
                  />
                </div>
                <div>
                  <Label htmlFor={`channel-${row.filing_request_id}`}>Channel</Label>
                  <Select
                    id={`channel-${row.filing_request_id}`}
                    className="w-36"
                    value={channel}
                    onChange={(e) => setChannel(e.target.value as ReminderChannel)}
                  >
                    <option value="email">Email</option>
                    <option value="whatsapp">WhatsApp</option>
                    <option value="sms">SMS</option>
                  </Select>
                </div>
                <Button type="submit" size="sm" disabled={createReminder.isPending}>
                  <BellRing size={14} />
                  {createReminder.isPending ? "Scheduling…" : "Schedule reminder"}
                </Button>
              </form>

              {isLoading ? (
                <Skeleton className="h-8 w-full" />
              ) : !reminders || reminders.length === 0 ? (
                <p className="text-xs text-[var(--ink-muted)]">No reminders scheduled for this filing yet.</p>
              ) : (
                <ul className="space-y-1.5">
                  {reminders.map((r) => (
                    <li
                      key={r.id}
                      className="flex items-center justify-between rounded-[var(--radius-sm)] border border-[var(--line)] px-3 py-2 text-sm"
                    >
                      <span className="text-[var(--ink)]">
                        {r.days_before_deadline}d before deadline via {r.channel}
                        {r.sent_at && (
                          <span className="ml-2 text-xs text-[var(--ink-muted)]">
                            sent {new Date(r.sent_at).toLocaleDateString()}
                          </span>
                        )}
                      </span>
                      {r.cancelled ? (
                        <Badge tone="neutral">Cancelled</Badge>
                      ) : (
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => cancelReminder.mutate(r.id)}
                          disabled={cancelReminder.isPending}
                        >
                          <BellOff size={14} />
                          Cancel
                        </Button>
                      )}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </td>
        </tr>
      )}
    </>
  );
}

export default function AutomationPage() {
  const { data, isLoading, isError, error } = useEscalations();

  if (isError) throw error;

  return (
    <div className="space-y-8">
      <div>
        <h1 className="font-[family-name:var(--font-display)] text-2xl text-[var(--ink)]">Automation</h1>
        <p className="mt-1 text-sm text-[var(--ink-muted)]">
          Filings with missing documents past their due date, and the deadline reminders configured for each.
        </p>
      </div>

      <Card>
        <CardHeader className="flex flex-row items-center gap-2">
          <AlertTriangle size={18} className="text-[var(--overdue)]" />
          <CardTitle>Escalations</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="space-y-3 p-5">
              {Array.from({ length: 4 }).map((_, i) => (
                <Skeleton key={i} className="h-10 w-full" />
              ))}
            </div>
          ) : !data || data.length === 0 ? (
            <div className="p-5">
              <EmptyState
                icon={AlertTriangle}
                title="Nothing overdue"
                description="No filings currently have missing documents past their due date."
              />
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-t border-[var(--line)] text-left text-xs uppercase tracking-wide text-[var(--ink-muted)]">
                  <th className="px-5 py-3 font-medium">Client</th>
                  <th className="px-5 py-3 font-medium">Missing</th>
                  <th className="px-5 py-3 font-medium">Due date</th>
                  <th className="px-5 py-3 font-medium">Overdue</th>
                  <th className="px-5 py-3 font-medium">Follow-ups sent</th>
                  <th className="px-5 py-3 font-medium" />
                </tr>
              </thead>
              <tbody>
                {data.map((row) => (
                  <ReminderRow key={row.filing_request_id} row={row} />
                ))}
              </tbody>
            </table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
