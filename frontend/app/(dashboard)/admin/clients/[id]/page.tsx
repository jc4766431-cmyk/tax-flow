"use client";

import { use, useState } from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { AxiosError } from "axios";
import { ArrowLeft, FileText, MessageCircle, Plus, FileSignature, Loader2, Send, Phone } from "lucide-react";
import { api } from "@/lib/api";
import { useCurrentUser } from "@/hooks/use-auth";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/dashboard/empty-state";
import { FilingTimeline } from "@/components/dashboard/filing-timeline";
import { NewFilingModal } from "@/components/dashboard/new-filing-modal";
import { FILING_TYPE_LABELS, type Client, type DocumentItem, type FilingRequest } from "@/lib/types";

function errorMessage(err: unknown, fallback: string) {
  if (err instanceof AxiosError) {
    const detail = err.response?.data?.detail;
    if (typeof detail === "string") return detail;
  }
  return fallback;
}

function useClient(clientId: string) {
  return useQuery<Client>({
    queryKey: ["clients", clientId],
    queryFn: async () => (await api.get(`/clients/${clientId}`)).data,
  });
}

// No client_id filter on GET /filings today, so fetch the firm's filings and
// filter client-side — same approach the Calendar page already takes.
function useClientFilings(clientId: string) {
  return useQuery<FilingRequest[]>({
    queryKey: ["filings", "all"],
    queryFn: async () => (await api.get("/filings")).data,
    select: (all) => all.filter((f) => f.client_id === clientId),
  });
}

export default function ClientOverviewPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { data: currentUser } = useCurrentUser();
  const queryClient = useQueryClient();
  const { data: client, isLoading, isError, error } = useClient(id);
  const { data: filings, isLoading: filingsLoading } = useClientFilings(id);
  const [newFilingOpen, setNewFilingOpen] = useState(false);
  const [downloading, setDownloading] = useState(false);

  if (isError) throw error;

  const generateLetter = useMutation({
    mutationFn: async () => {
      const { data: document } = await api.post<DocumentItem>(
        `/clients/${id}/engagement-letter`
      );
      return document;
    },
    onSuccess: async (document) => {
      toast.success("Engagement letter generated");
      queryClient.invalidateQueries({ queryKey: ["documents", "review"] });
      setDownloading(true);
      try {
        const { data } = await api.get(`/documents/${document.id}/download-url`);
        window.open(data.download_url, "_blank", "noopener,noreferrer");
      } catch {
        toast.error("Letter was generated, but the download link couldn't be fetched.");
      } finally {
        setDownloading(false);
      }
    },
    onError: (err) => toast.error(errorMessage(err, "Couldn't generate an engagement letter.")),
  });

  const invitePortalAccess = useMutation({
    mutationFn: async () => (await api.post(`/clients/${id}/invite-portal-access`)).data,
    onSuccess: () => {
      toast.success("Portal access invite sent over WhatsApp");
      queryClient.invalidateQueries({ queryKey: ["clients", id] });
    },
    onError: (err) => toast.error(errorMessage(err, "Couldn't send that invite.")),
  });

  return (
    <div className="space-y-6">
      <Link
        href="/admin/clients"
        className="inline-flex items-center gap-1 text-sm text-[var(--ink-muted)] hover:text-[var(--ink)]"
      >
        <ArrowLeft size={14} /> Back to clients
      </Link>

      {isLoading || !client ? (
        <Skeleton className="h-24 w-full" />
      ) : (
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <h1 className="font-[family-name:var(--font-display)] text-2xl font-semibold text-[var(--ink)]">
              {client.company_name ?? "Unnamed client"}
            </h1>
            <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-[var(--ink-muted)]">
              <span>PAN: {client.pan_number ?? "—"}</span>
              <span>GSTIN: {client.gstin ?? "—"}</span>
              {client.phone && (
                <span className="inline-flex items-center gap-1">
                  <Phone size={12} /> {client.phone}
                </span>
              )}
              <Badge tone={client.has_portal_access ? "verified" : "pending"}>
                {client.has_portal_access ? "Portal access" : "WhatsApp-only"}
              </Badge>
              <Badge tone={client.assigned_accountant_id ? "verified" : "pending"}>
                {client.assigned_accountant_id ? "Accountant assigned" : "Unassigned"}
              </Badge>
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            <Link href={`/admin/clients/${id}/messages`}>
              <Button variant="outline">
                <MessageCircle size={16} /> Messages
              </Button>
            </Link>
            {!client.has_portal_access && (
              <Button
                variant="outline"
                onClick={() => invitePortalAccess.mutate()}
                disabled={invitePortalAccess.isPending || !client.phone}
              >
                {invitePortalAccess.isPending ? (
                  <Loader2 size={16} className="animate-spin" />
                ) : (
                  <Send size={16} />
                )}
                Invite to web portal
              </Button>
            )}
            <Button
              variant="outline"
              onClick={() => generateLetter.mutate()}
              disabled={generateLetter.isPending || downloading}
            >
              {generateLetter.isPending || downloading ? (
                <Loader2 size={16} className="animate-spin" />
              ) : (
                <FileSignature size={16} />
              )}
              Generate engagement letter
            </Button>
          </div>
        </div>
      )}

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <FileText size={18} className="text-[var(--ink-muted)]" />
            Filings
          </CardTitle>
          <Button size="sm" onClick={() => setNewFilingOpen(true)}>
            <Plus size={14} /> New filing
          </Button>
        </CardHeader>
        <CardContent>
          {filingsLoading || !filings ? (
            <div className="space-y-3">
              {Array.from({ length: 2 }).map((_, i) => (
                <Skeleton key={i} className="h-20 w-full" />
              ))}
            </div>
          ) : filings.length === 0 ? (
            <EmptyState
              icon={FileText}
              title="No filings yet"
              description="Filings you open for this client will show up here."
            />
          ) : (
            <div className="divide-y divide-[var(--line)]">
              {filings.map((f) => (
                <div key={f.id} className="py-2">
                  <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm">
                    <span className="font-medium text-[var(--ink)]">
                      {FILING_TYPE_LABELS[f.filing_type]}
                    </span>
                    {f.period_label && (
                      <span className="text-[var(--ink-muted)]">{f.period_label}</span>
                    )}
                    {f.due_date && (
                      <span className="tabular text-xs text-[var(--ink-muted)]">
                        Due {new Date(f.due_date).toLocaleDateString("en-IN")}
                      </span>
                    )}
                  </div>
                  <FilingTimeline filingId={f.id} />
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <NewFilingModal
        open={newFilingOpen}
        onClose={() => setNewFilingOpen(false)}
        clientId={id}
        firmId={currentUser?.firm_id ?? undefined}
      />
    </div>
  );
}
