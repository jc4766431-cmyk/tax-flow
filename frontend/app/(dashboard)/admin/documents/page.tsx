"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import {
  FileSearch,
  Download,
  CheckCircle2,
  XCircle,
  Loader2,
} from "lucide-react";
import { api } from "@/lib/api";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Select } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/dashboard/empty-state";
import { Modal } from "@/components/dashboard/modal";
import { useClientsList } from "@/hooks/use-clients";
import {
  DOCUMENT_CATEGORY_LABELS,
  type DocumentCategory,
  type DocumentItem,
  type DocumentStatus,
  type PaginatedDocuments,
} from "@/lib/types";

const STATUS_OPTIONS: { value: DocumentStatus | ""; label: string }[] = [
  { value: "uploaded", label: "Awaiting review" },
  { value: "under_review", label: "Under review" },
  { value: "approved", label: "Approved" },
  { value: "rejected", label: "Rejected" },
  { value: "", label: "All statuses" },
];

function statusTone(status: DocumentStatus) {
  switch (status) {
    case "approved":
      return "verified" as const;
    case "rejected":
      return "overdue" as const;
    case "missing":
      return "neutral" as const;
    default:
      return "pending" as const;
  }
}

function statusLabel(status: DocumentStatus) {
  switch (status) {
    case "approved":
      return "Approved";
    case "rejected":
      return "Rejected";
    case "under_review":
      return "Under review";
    case "uploaded":
      return "Awaiting review";
    default:
      return "Missing";
  }
}

function formatBytes(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function useDocuments(status: DocumentStatus | "", clientId: string, category: DocumentCategory | "") {
  return useQuery<PaginatedDocuments>({
    queryKey: ["documents", "review", status, clientId, category],
    queryFn: async () =>
      (
        await api.get("/documents", {
          params: {
            status: status || undefined,
            client_id: clientId || undefined,
            category: category || undefined,
            page: 1,
            page_size: 50,
          },
        })
      ).data,
  });
}

function RejectModal({
  document,
  onClose,
}: {
  document: DocumentItem | null;
  onClose: () => void;
}) {
  const queryClient = useQueryClient();
  const [comment, setComment] = useState("");

  const reject = useMutation({
    mutationFn: async () =>
      (
        await api.patch(`/documents/${document!.id}/status`, {
          status: "rejected",
          reviewer_comment: comment || null,
        })
      ).data,
    onSuccess: () => {
      toast.success("Document rejected — client will be asked to re-upload.");
      queryClient.invalidateQueries({ queryKey: ["documents", "review"] });
      setComment("");
      onClose();
    },
    onError: () => toast.error("Couldn't reject that document."),
  });

  return (
    <Modal
      open={!!document}
      onClose={onClose}
      title={`Reject ${document?.original_filename ?? ""}`}
    >
      <form
        className="space-y-4"
        onSubmit={(e) => {
          e.preventDefault();
          reject.mutate();
        }}
      >
        <p className="text-sm text-[var(--ink-muted)]">
          The client will see this document marked for re-upload. Let them know why.
        </p>
        <Textarea
          rows={3}
          placeholder="e.g. Image is blurry — please re-upload a clearer scan."
          value={comment}
          onChange={(e) => setComment(e.target.value)}
        />
        <div className="flex justify-end gap-2">
          <Button type="button" variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" disabled={reject.isPending}>
            {reject.isPending ? "Rejecting…" : "Reject document"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

export default function DocumentReviewPage() {
  const [statusFilter, setStatusFilter] = useState<DocumentStatus | "">("uploaded");
  const [clientFilter, setClientFilter] = useState("");
  const [categoryFilter, setCategoryFilter] = useState<DocumentCategory | "">("");
  const [rejectTarget, setRejectTarget] = useState<DocumentItem | null>(null);
  const [downloadingId, setDownloadingId] = useState<string | null>(null);

  const { data: clientsPage } = useClientsList();
  const clients = clientsPage?.items ?? [];
  const clientName = (id: string) =>
    clients.find((c) => c.id === id)?.company_name ?? id.slice(0, 8);

  const { data, isLoading, isError, error } = useDocuments(
    statusFilter,
    clientFilter,
    categoryFilter
  );
  const queryClient = useQueryClient();

  if (isError) throw error;

  const approve = useMutation({
    mutationFn: async (id: string) =>
      (await api.patch(`/documents/${id}/status`, { status: "approved" })).data,
    onSuccess: () => {
      toast.success("Document approved.");
      queryClient.invalidateQueries({ queryKey: ["documents", "review"] });
    },
    onError: () => toast.error("Couldn't approve that document."),
  });

  async function handleDownload(doc: DocumentItem) {
    setDownloadingId(doc.id);
    try {
      const { data } = await api.get(`/documents/${doc.id}/download-url`);
      window.open(data.download_url, "_blank", "noopener,noreferrer");
    } catch {
      toast.error("Couldn't get a download link for that document.");
    } finally {
      setDownloadingId(null);
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-[family-name:var(--font-display)] text-2xl font-semibold text-[var(--ink)]">
          Document review
        </h1>
        <p className="mt-1 text-sm text-[var(--ink-muted)]">
          Approve or reject documents your clients have uploaded.
        </p>
      </div>

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <div className="w-full sm:w-52">
          <Select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value as DocumentStatus | "")}
          >
            {STATUS_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </Select>
        </div>
        <div className="w-full sm:w-56">
          <Select
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value as DocumentCategory | "")}
          >
            <option value="">All categories</option>
            {Object.entries(DOCUMENT_CATEGORY_LABELS).map(([key, label]) => (
              <option key={key} value={key}>
                {label}
              </option>
            ))}
          </Select>
        </div>
        <div className="w-full sm:w-56">
          <Select value={clientFilter} onChange={(e) => setClientFilter(e.target.value)}>
            <option value="">All clients</option>
            {clients.map((c) => (
              <option key={c.id} value={c.id}>
                {c.company_name ?? c.id.slice(0, 8)}
              </option>
            ))}
          </Select>
        </div>
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
                icon={FileSearch}
                title="Nothing to review"
                description="Documents matching this filter will show up here."
              />
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-[var(--line)] text-xs uppercase tracking-wide text-[var(--ink-muted)]">
                    <th className="px-5 py-3 font-medium">File</th>
                    <th className="px-5 py-3 font-medium">Client</th>
                    <th className="px-5 py-3 font-medium">Category</th>
                    <th className="px-5 py-3 font-medium">Status</th>
                    <th className="px-5 py-3 font-medium">Size</th>
                    <th className="px-5 py-3 font-medium" />
                  </tr>
                </thead>
                <tbody className="divide-y divide-[var(--line)]">
                  {data.items.map((doc) => (
                    <tr key={doc.id} className="hover:bg-[var(--surface-hover)]">
                      <td className="max-w-[16rem] truncate px-5 py-3 font-medium text-[var(--ink)]">
                        {doc.original_filename}
                        {doc.reviewer_comment && (
                          <p className="mt-0.5 truncate text-xs font-normal text-[var(--ink-muted)]">
                            &ldquo;{doc.reviewer_comment}&rdquo;
                          </p>
                        )}
                      </td>
                      <td className="px-5 py-3 text-[var(--ink-muted)]">
                        {clientName(doc.client_id)}
                      </td>
                      <td className="px-5 py-3 text-[var(--ink-muted)]">
                        {DOCUMENT_CATEGORY_LABELS[doc.category] ?? doc.category}
                      </td>
                      <td className="px-5 py-3">
                        <Badge tone={statusTone(doc.status)}>{statusLabel(doc.status)}</Badge>
                      </td>
                      <td className="tabular px-5 py-3 text-[var(--ink-muted)]">
                        {formatBytes(doc.file_size_bytes)}
                      </td>
                      <td className="px-5 py-3">
                        <div className="flex items-center justify-end gap-1">
                          <button
                            title="Download"
                            onClick={() => handleDownload(doc)}
                            disabled={downloadingId === doc.id}
                            className="rounded-[var(--radius-sm)] p-1.5 text-[var(--ink-muted)] transition-colors hover:bg-[var(--surface)] hover:text-[var(--ink)]"
                          >
                            {downloadingId === doc.id ? (
                              <Loader2 size={14} className="animate-spin" />
                            ) : (
                              <Download size={14} />
                            )}
                          </button>
                          {(doc.status === "uploaded" || doc.status === "under_review") && (
                            <>
                              <button
                                title="Approve"
                                onClick={() => approve.mutate(doc.id)}
                                className="rounded-[var(--radius-sm)] p-1.5 text-[var(--ink-muted)] transition-colors hover:bg-[var(--surface)] hover:text-[var(--verified)]"
                              >
                                <CheckCircle2 size={14} />
                              </button>
                              <button
                                title="Reject"
                                onClick={() => setRejectTarget(doc)}
                                className="rounded-[var(--radius-sm)] p-1.5 text-[var(--ink-muted)] transition-colors hover:bg-[var(--surface)] hover:text-[var(--overdue)]"
                              >
                                <XCircle size={14} />
                              </button>
                            </>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      <RejectModal document={rejectTarget} onClose={() => setRejectTarget(null)} />
    </div>
  );
}
