"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  MessageSquare,
  Image as ImageIcon,
  FileText,
  HelpCircle,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import { api } from "@/lib/api";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Select } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/dashboard/empty-state";
import { useClientsList } from "@/hooks/use-clients";
import type { WhatsAppInboundMessagePage, WhatsAppProcessingStatus } from "@/lib/types";

const PAGE_SIZE = 20;

const STATUS_OPTIONS: { value: WhatsAppProcessingStatus | ""; label: string }[] = [
  { value: "", label: "All statuses" },
  { value: "received", label: "Received" },
  { value: "unmatched", label: "Unmatched (unknown number)" },
  { value: "acknowledged", label: "Acknowledged" },
  { value: "document_created", label: "Document created" },
  { value: "error", label: "Error" },
];

function statusTone(status: WhatsAppProcessingStatus) {
  switch (status) {
    case "document_created":
      return "verified" as const;
    case "error":
    case "unmatched":
      return "overdue" as const;
    case "acknowledged":
      return "pending" as const;
    default:
      return "neutral" as const;
  }
}

function messageTypeIcon(type: string) {
  if (type === "image" || type === "document") return ImageIcon;
  if (type === "text") return FileText;
  return HelpCircle;
}

function useWhatsAppMessages(status: WhatsAppProcessingStatus | "", page: number) {
  return useQuery<WhatsAppInboundMessagePage>({
    queryKey: ["whatsapp", "messages", status, page],
    queryFn: async () =>
      (
        await api.get("/webhooks/whatsapp/messages", {
          params: { status: status || undefined, page, page_size: PAGE_SIZE },
        })
      ).data,
  });
}

export default function WhatsAppPage() {
  const [statusFilter, setStatusFilter] = useState<WhatsAppProcessingStatus | "">("");
  const [page, setPage] = useState(1);
  const { data, isLoading, isError, error } = useWhatsAppMessages(statusFilter, page);
  const { data: clientsPage } = useClientsList();
  const clients = clientsPage?.items ?? [];
  const clientName = (id: string | null) =>
    id ? clients.find((c) => c.id === id)?.company_name ?? id.slice(0, 8) : "—";

  if (isError) throw error;

  const totalPages = data ? Math.max(1, Math.ceil(data.total / data.page_size)) : 1;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-[family-name:var(--font-display)] text-2xl font-semibold text-[var(--ink)]">
          WhatsApp
        </h1>
        <p className="mt-1 text-sm text-[var(--ink-muted)]">
          Inbound messages from clients, and what came of each one.
        </p>
      </div>

      <div className="w-full sm:w-72">
        <Select
          value={statusFilter}
          onChange={(e) => {
            setStatusFilter(e.target.value as WhatsAppProcessingStatus | "");
            setPage(1);
          }}
        >
          {STATUS_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </Select>
      </div>

      <Card>
        <CardContent className="p-0">
          {isLoading || !data ? (
            <div className="space-y-3 p-5">
              {Array.from({ length: 5 }).map((_, i) => (
                <Skeleton key={i} className="h-10 w-full" />
              ))}
            </div>
          ) : data.items.length === 0 ? (
            <div className="p-5">
              <EmptyState
                icon={MessageSquare}
                title="No WhatsApp messages yet"
                description="Messages clients send to your WhatsApp number will show up here as they arrive."
              />
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-[var(--line)] text-xs uppercase tracking-wide text-[var(--ink-muted)]">
                    <th className="px-5 py-3 font-medium">From</th>
                    <th className="px-5 py-3 font-medium">Client</th>
                    <th className="px-5 py-3 font-medium">Type</th>
                    <th className="px-5 py-3 font-medium">Result</th>
                    <th className="px-5 py-3 font-medium">Detail</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[var(--line)]">
                  {data.items.map((msg) => {
                    const Icon = messageTypeIcon(msg.message_type);
                    return (
                      <tr key={msg.id} className="hover:bg-[var(--surface-hover)]">
                        <td className="tabular px-5 py-3 font-medium text-[var(--ink)]">
                          {msg.from_phone}
                        </td>
                        <td className="px-5 py-3 text-[var(--ink-muted)]">
                          {clientName(msg.client_id)}
                        </td>
                        <td className="px-5 py-3 text-[var(--ink-muted)]">
                          <span className="inline-flex items-center gap-1.5">
                            <Icon size={13} />
                            {msg.message_type}
                          </span>
                        </td>
                        <td className="px-5 py-3">
                          <Badge tone={statusTone(msg.processing_status)}>
                            {msg.processing_status.replace(/_/g, " ")}
                          </Badge>
                        </td>
                        <td className="max-w-[16rem] truncate px-5 py-3 text-xs text-[var(--ink-muted)]">
                          {msg.error_detail ??
                            (msg.created_document_id ? "Document created from this message" : "—")}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {data && data.total > 0 && (
        <div className="flex items-center justify-between text-sm text-[var(--ink-muted)]">
          <p>
            <span className="tabular">
              {(data.page - 1) * data.page_size + 1}–
              {Math.min(data.page * data.page_size, data.total)}
            </span>{" "}
            of <span className="tabular">{data.total}</span> messages
          </p>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page <= 1}
            >
              <ChevronLeft size={14} /> Prev
            </Button>
            <span className="tabular px-1">
              {page} / {totalPages}
            </span>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page >= totalPages}
            >
              Next <ChevronRight size={14} />
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
