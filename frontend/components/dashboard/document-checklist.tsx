"use client";

import { useCallback, useState } from "react";
import { useDropzone } from "react-dropzone";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { UploadCloud, CheckCircle2, Loader2 } from "lucide-react";
import { api } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  DOCUMENT_CATEGORY_LABELS,
  type ChecklistItem,
} from "@/lib/types";

/**
 * Client-portal document upload + checklist (HANDOFF.md "Document upload UI
 * on the client portal" item). Drives the existing, already-built backend
 * flow end to end: GET the checklist, then for any missing/rejected item,
 * drag-and-drop a file which is (1) presigned, (2) PUT to S3 directly, then
 * (3) registered via POST /documents — exactly the three-step flow
 * documents.py's docstrings describe.
 */
function statusTone(status: ChecklistItem["status"]) {
  if (status === "approved") return "verified" as const;
  if (status === "rejected") return "overdue" as const;
  if (status === "missing") return "neutral" as const;
  return "pending" as const;
}

function statusLabel(status: ChecklistItem["status"]) {
  switch (status) {
    case "approved":
      return "Approved";
    case "rejected":
      return "Rejected — re-upload";
    case "under_review":
      return "Under review";
    case "uploaded":
      return "Uploaded";
    default:
      return "Missing";
  }
}

function ChecklistRow({
  item,
  clientId,
  filingRequestId,
}: {
  item: ChecklistItem;
  clientId: string;
  filingRequestId: string;
}) {
  const queryClient = useQueryClient();
  const [error, setError] = useState<string | null>(null);

  const upload = useMutation({
    mutationFn: async (file: File) => {
      const { data: presigned } = await api.post("/documents/presigned-upload", {
        client_id: clientId,
        original_filename: file.name,
        mime_type: file.type || "application/octet-stream",
      });

      await fetch(presigned.upload_url, {
        method: "PUT",
        headers: { "Content-Type": file.type || "application/octet-stream" },
        body: file,
      });

      await api.post("/documents", {
        client_id: clientId,
        filing_request_id: filingRequestId,
        category: item.category,
        storage_key: presigned.storage_key,
        original_filename: file.name,
        mime_type: file.type || "application/octet-stream",
        file_size_bytes: file.size,
      });
    },
    onSuccess: () => {
      setError(null);
      queryClient.invalidateQueries({ queryKey: ["checklist", filingRequestId] });
    },
    onError: () => setError("Upload failed — please try again."),
  });

  const onDrop = useCallback(
    (accepted: File[]) => {
      if (accepted[0]) upload.mutate(accepted[0]);
    },
    [upload]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    multiple: false,
    disabled: upload.isPending,
  });

  const canUpload = item.status === "missing" || item.status === "rejected";

  return (
    <li className="flex flex-col gap-2 py-3 first:pt-0 last:pb-0 sm:flex-row sm:items-center sm:justify-between">
      <div className="flex items-center gap-2">
        {item.status === "approved" && (
          <CheckCircle2 size={16} className="text-[var(--verified)]" />
        )}
        <span className="text-sm font-medium text-[var(--ink)]">
          {DOCUMENT_CATEGORY_LABELS[item.category]}
        </span>
        {item.required && (
          <span className="text-xs text-[var(--ink-muted)]">required</span>
        )}
      </div>

      <div className="flex items-center gap-3">
        <Badge tone={statusTone(item.status)}>{statusLabel(item.status)}</Badge>

        {canUpload && (
          <div
            {...getRootProps()}
            className={`flex cursor-pointer items-center gap-1.5 rounded-[var(--radius-sm)] border border-dashed px-3 py-1.5 text-xs transition-colors ${
              isDragActive
                ? "border-[var(--brass)] bg-[var(--brass)]/10"
                : "border-[var(--line)] text-[var(--ink-muted)] hover:border-[var(--brass)]/50"
            }`}
          >
            <input {...getInputProps()} />
            {upload.isPending ? (
              <Loader2 size={14} className="animate-spin" />
            ) : (
              <UploadCloud size={14} />
            )}
            {upload.isPending ? "Uploading…" : "Upload"}
          </div>
        )}
      </div>
      {error && <p className="text-xs text-[var(--overdue)] sm:hidden">{error}</p>}
    </li>
  );
}

export function DocumentChecklist({
  filingId,
  clientId,
}: {
  filingId: string;
  clientId: string;
}) {
  const { data, isLoading } = useQuery<ChecklistItem[]>({
    queryKey: ["checklist", filingId],
    queryFn: async () => (await api.get(`/documents/checklist/${filingId}`)).data,
  });

  if (isLoading || !data) {
    return (
      <div className="space-y-2 py-2">
        <Skeleton className="h-8 w-full" />
        <Skeleton className="h-8 w-full" />
      </div>
    );
  }

  return (
    <div className="border-t border-[var(--line)] pt-3">
      <p className="mb-1 text-xs font-medium uppercase tracking-wide text-[var(--ink-muted)]">
        Documents
      </p>
      <ul className="divide-y divide-[var(--line)]">
        {data.map((item) => (
          <ChecklistRow
            key={item.id}
            item={item}
            clientId={clientId}
            filingRequestId={filingId}
          />
        ))}
      </ul>
    </div>
  );
}
