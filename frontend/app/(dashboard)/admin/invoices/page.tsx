"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import {
  FileText,
  Plus,
  Send,
  CheckCircle2,
  Ban,
  Trash2,
  X as XIcon,
} from "lucide-react";
import { api } from "@/lib/api";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/dashboard/empty-state";
import { Modal } from "@/components/dashboard/modal";
import { useClientsList } from "@/hooks/use-clients";
import type { Invoice, InvoiceLineItem, InvoiceStatus } from "@/lib/types";

const STATUS_OPTIONS: { value: InvoiceStatus | ""; label: string }[] = [
  { value: "", label: "All statuses" },
  { value: "draft", label: "Draft" },
  { value: "sent", label: "Sent" },
  { value: "paid", label: "Paid" },
  { value: "overdue", label: "Overdue" },
  { value: "cancelled", label: "Cancelled" },
];

function statusTone(status: InvoiceStatus) {
  switch (status) {
    case "paid":
      return "verified" as const;
    case "overdue":
      return "overdue" as const;
    case "sent":
      return "pending" as const;
    case "cancelled":
      return "neutral" as const;
    default:
      return "neutral" as const;
  }
}

function formatINR(amount: number) {
  return `₹${amount.toLocaleString("en-IN", { maximumFractionDigits: 2 })}`;
}

function useInvoices(status: InvoiceStatus | "", clientId: string) {
  return useQuery<Invoice[]>({
    queryKey: ["invoices", status, clientId],
    queryFn: async () =>
      (
        await api.get("/invoices", {
          params: {
            status: status || undefined,
            client_id: clientId || undefined,
          },
        })
      ).data,
  });
}

// --- Create invoice form ---------------------------------------------

function emptyLineItem(): InvoiceLineItem {
  return { description: "", quantity: 1, unit_amount: 0 };
}

function CreateInvoiceModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const queryClient = useQueryClient();
  const { data: clientsPage } = useClientsList();
  const clients = clientsPage?.items ?? [];

  function defaultIssueDate() {
    return new Date().toISOString().slice(0, 10);
  }
  function defaultDueDate() {
    return new Date(Date.now() + 14 * 24 * 60 * 60 * 1000).toISOString().slice(0, 10);
  }

  const [clientId, setClientId] = useState("");
  const [issueDate, setIssueDate] = useState(defaultIssueDate);
  const [dueDate, setDueDate] = useState(defaultDueDate);
  const [taxRate, setTaxRate] = useState("18");
  const [notes, setNotes] = useState("");
  const [lineItems, setLineItems] = useState<InvoiceLineItem[]>([emptyLineItem()]);

  function reset() {
    setClientId("");
    setIssueDate(defaultIssueDate());
    setDueDate(defaultDueDate());
    setTaxRate("18");
    setNotes("");
    setLineItems([emptyLineItem()]);
  }

  const create = useMutation({
    mutationFn: async () =>
      (
        await api.post("/invoices", {
          client_id: clientId,
          issue_date: issueDate,
          due_date: dueDate,
          tax_rate: Number(taxRate) || 0,
          notes: notes || null,
          line_items: lineItems.filter((li) => li.description.trim() !== ""),
        })
      ).data,
    onSuccess: () => {
      toast.success("Invoice created as a draft.");
      queryClient.invalidateQueries({ queryKey: ["invoices"] });
      reset();
      onClose();
    },
    onError: () => toast.error("Couldn't create that invoice. Check the fields and try again."),
  });

  const subtotal = lineItems.reduce(
    (sum, li) => sum + (Number(li.quantity) || 0) * (Number(li.unit_amount) || 0),
    0
  );
  const taxAmount = subtotal * ((Number(taxRate) || 0) / 100);
  const total = subtotal + taxAmount;

  function updateLine(idx: number, patch: Partial<InvoiceLineItem>) {
    setLineItems((items) => items.map((li, i) => (i === idx ? { ...li, ...patch } : li)));
  }

  const canSubmit =
    clientId !== "" &&
    issueDate !== "" &&
    dueDate !== "" &&
    lineItems.some((li) => li.description.trim() !== "" && li.unit_amount > 0);

  return (
    <Modal open={open} onClose={onClose} title="New invoice" maxWidth="max-w-2xl">
      <form
        className="space-y-5"
        onSubmit={(e) => {
          e.preventDefault();
          if (canSubmit) create.mutate();
        }}
      >
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <div className="sm:col-span-1">
            <Label>Client</Label>
            <Select value={clientId} onChange={(e) => setClientId(e.target.value)} required>
              <option value="">Select a client…</option>
              {clients.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.company_name ?? c.pan_number ?? c.id.slice(0, 8)}
                </option>
              ))}
            </Select>
          </div>
          <div>
            <Label>Issue date</Label>
            <Input
              type="date"
              value={issueDate}
              onChange={(e) => setIssueDate(e.target.value)}
              required
            />
          </div>
          <div>
            <Label>Due date</Label>
            <Input
              type="date"
              value={dueDate}
              onChange={(e) => setDueDate(e.target.value)}
              required
            />
          </div>
        </div>

        <div>
          <Label>Line items</Label>
          <div className="space-y-2">
            {lineItems.map((li, idx) => (
              <div key={idx} className="flex items-start gap-2">
                <Input
                  className="flex-1"
                  placeholder="Description"
                  value={li.description}
                  onChange={(e) => updateLine(idx, { description: e.target.value })}
                />
                <Input
                  type="number"
                  min={0}
                  step="0.01"
                  className="w-24"
                  placeholder="Qty"
                  value={li.quantity}
                  onChange={(e) => updateLine(idx, { quantity: Number(e.target.value) })}
                />
                <Input
                  type="number"
                  min={0}
                  step="0.01"
                  className="w-32"
                  placeholder="Unit amount"
                  value={li.unit_amount}
                  onChange={(e) => updateLine(idx, { unit_amount: Number(e.target.value) })}
                />
                <button
                  type="button"
                  onClick={() => setLineItems((items) => items.filter((_, i) => i !== idx))}
                  disabled={lineItems.length === 1}
                  className="flex h-10 w-10 items-center justify-center rounded-[var(--radius-sm)] text-[var(--ink-muted)] transition-colors hover:bg-[var(--surface)] hover:text-[var(--overdue)] disabled:opacity-30"
                >
                  <XIcon size={16} />
                </button>
              </div>
            ))}
          </div>
          <button
            type="button"
            onClick={() => setLineItems((items) => [...items, emptyLineItem()])}
            className="mt-2 inline-flex items-center gap-1.5 text-xs font-medium text-[var(--brass)] hover:text-[var(--brass-hover)]"
          >
            <Plus size={14} /> Add line item
          </button>
        </div>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div>
            <Label>Tax rate (%)</Label>
            <Input
              type="number"
              min={0}
              step="0.01"
              value={taxRate}
              onChange={(e) => setTaxRate(e.target.value)}
            />
          </div>
          <div>
            <Label>Notes (optional)</Label>
            <Textarea rows={1} value={notes} onChange={(e) => setNotes(e.target.value)} />
          </div>
        </div>

        <div className="rounded-[var(--radius-sm)] border border-[var(--line)] bg-[var(--surface)] p-4 text-sm">
          <div className="flex justify-between text-[var(--ink-muted)]">
            <span>Subtotal</span>
            <span className="tabular">{formatINR(subtotal)}</span>
          </div>
          <div className="flex justify-between text-[var(--ink-muted)]">
            <span>Tax ({taxRate || 0}%)</span>
            <span className="tabular">{formatINR(taxAmount)}</span>
          </div>
          <div className="mt-1 flex justify-between border-t border-[var(--line)] pt-1 font-medium text-[var(--ink)]">
            <span>Total</span>
            <span className="tabular">{formatINR(total)}</span>
          </div>
        </div>

        <div className="flex justify-end gap-2">
          <Button type="button" variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" disabled={!canSubmit || create.isPending}>
            {create.isPending ? "Creating…" : "Create draft invoice"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

// --- Mark paid modal ---------------------------------------------------

function MarkPaidModal({
  invoice,
  onClose,
}: {
  invoice: Invoice | null;
  onClose: () => void;
}) {
  const queryClient = useQueryClient();
  const [paidAt, setPaidAt] = useState(new Date().toISOString().slice(0, 10));
  const [reference, setReference] = useState("");

  const markPaid = useMutation({
    mutationFn: async () =>
      (
        await api.post(`/invoices/${invoice!.id}/mark-paid`, {
          paid_at: paidAt,
          payment_reference: reference || null,
        })
      ).data,
    onSuccess: () => {
      toast.success("Invoice marked as paid.");
      queryClient.invalidateQueries({ queryKey: ["invoices"] });
      onClose();
    },
    onError: () => toast.error("Couldn't mark that invoice as paid."),
  });

  return (
    <Modal open={!!invoice} onClose={onClose} title={`Mark ${invoice?.invoice_number} as paid`}>
      <form
        className="space-y-4"
        onSubmit={(e) => {
          e.preventDefault();
          markPaid.mutate();
        }}
      >
        <div>
          <Label>Payment date</Label>
          <Input type="date" value={paidAt} onChange={(e) => setPaidAt(e.target.value)} />
        </div>
        <div>
          <Label>Payment reference (optional)</Label>
          <Input
            placeholder="UPI ref, cheque no., bank transfer id…"
            value={reference}
            onChange={(e) => setReference(e.target.value)}
          />
        </div>
        <div className="flex justify-end gap-2">
          <Button type="button" variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" disabled={markPaid.isPending}>
            {markPaid.isPending ? "Saving…" : "Mark as paid"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

// --- Page ---------------------------------------------------------------

export default function InvoicesPage() {
  const [statusFilter, setStatusFilter] = useState<InvoiceStatus | "">("");
  const [clientFilter, setClientFilter] = useState("");
  const [createOpen, setCreateOpen] = useState(false);
  const [markPaidTarget, setMarkPaidTarget] = useState<Invoice | null>(null);

  const { data: clientsPage } = useClientsList();
  const clients = clientsPage?.items ?? [];
  const clientName = (id: string) =>
    clients.find((c) => c.id === id)?.company_name ?? id.slice(0, 8);

  const { data: invoices, isLoading, isError, error } = useInvoices(statusFilter, clientFilter);
  const queryClient = useQueryClient();

  if (isError) throw error;

  const sendInvoice = useMutation({
    mutationFn: async (id: string) => (await api.post(`/invoices/${id}/send`)).data,
    onSuccess: () => {
      toast.success("Invoice sent.");
      queryClient.invalidateQueries({ queryKey: ["invoices"] });
    },
    onError: () => toast.error("Couldn't send that invoice."),
  });

  const cancelInvoice = useMutation({
    mutationFn: async (id: string) => (await api.post(`/invoices/${id}/cancel`)).data,
    onSuccess: () => {
      toast.success("Invoice cancelled.");
      queryClient.invalidateQueries({ queryKey: ["invoices"] });
    },
    onError: () => toast.error("Couldn't cancel that invoice."),
  });

  const deleteInvoice = useMutation({
    mutationFn: async (id: string) => api.delete(`/invoices/${id}`),
    onSuccess: () => {
      toast.success("Invoice deleted.");
      queryClient.invalidateQueries({ queryKey: ["invoices"] });
    },
    onError: () => toast.error("Couldn't delete that invoice."),
  });

  const totalRevenue = (invoices ?? [])
    .filter((inv) => inv.status === "paid")
    .reduce((sum, inv) => sum + Number(inv.total_amount), 0);

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="font-[family-name:var(--font-display)] text-2xl font-semibold text-[var(--ink)]">
            Invoices
          </h1>
          <p className="mt-1 text-sm text-[var(--ink-muted)]">
            Bill your clients and track payment status.
          </p>
        </div>
        <Button onClick={() => setCreateOpen(true)}>
          <Plus size={16} /> New invoice
        </Button>
      </div>

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <div className="w-full sm:w-48">
          <Select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value as InvoiceStatus | "")}
          >
            {STATUS_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </Select>
        </div>
        <div className="w-full sm:w-64">
          <Select value={clientFilter} onChange={(e) => setClientFilter(e.target.value)}>
            <option value="">All clients</option>
            {clients.map((c) => (
              <option key={c.id} value={c.id}>
                {c.company_name ?? c.id.slice(0, 8)}
              </option>
            ))}
          </Select>
        </div>
        {invoices && invoices.length > 0 && (
          <p className="tabular text-sm text-[var(--ink-muted)] sm:ml-auto">
            {formatINR(totalRevenue)} collected in this view
          </p>
        )}
      </div>

      <Card>
        <CardContent className="p-0">
          {isLoading || !invoices ? (
            <div className="space-y-3 p-5">
              {Array.from({ length: 5 }).map((_, i) => (
                <Skeleton key={i} className="h-10 w-full" />
              ))}
            </div>
          ) : invoices.length === 0 ? (
            <div className="p-5">
              <EmptyState
                icon={FileText}
                title="No invoices yet"
                description="Create your first invoice to start billing a client."
              />
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-[var(--line)] text-xs uppercase tracking-wide text-[var(--ink-muted)]">
                    <th className="px-5 py-3 font-medium">Invoice #</th>
                    <th className="px-5 py-3 font-medium">Client</th>
                    <th className="px-5 py-3 font-medium">Status</th>
                    <th className="px-5 py-3 font-medium">Issue date</th>
                    <th className="px-5 py-3 font-medium">Due date</th>
                    <th className="px-5 py-3 font-medium">Total</th>
                    <th className="px-5 py-3 font-medium" />
                  </tr>
                </thead>
                <tbody className="divide-y divide-[var(--line)]">
                  {invoices.map((inv) => (
                    <tr key={inv.id} className="hover:bg-[var(--surface-hover)]">
                      <td className="px-5 py-3 font-medium text-[var(--ink)]">
                        {inv.invoice_number}
                      </td>
                      <td className="px-5 py-3 text-[var(--ink-muted)]">
                        {clientName(inv.client_id)}
                      </td>
                      <td className="px-5 py-3">
                        <Badge tone={statusTone(inv.status)}>{inv.status}</Badge>
                      </td>
                      <td className="tabular px-5 py-3 text-[var(--ink-muted)]">
                        {inv.issue_date}
                      </td>
                      <td className="tabular px-5 py-3 text-[var(--ink-muted)]">
                        {inv.due_date}
                      </td>
                      <td className="tabular px-5 py-3 font-medium text-[var(--ink)]">
                        {formatINR(Number(inv.total_amount))}
                      </td>
                      <td className="px-5 py-3">
                        <div className="flex items-center justify-end gap-1">
                          {inv.status === "draft" && (
                            <button
                              title="Send"
                              onClick={() => sendInvoice.mutate(inv.id)}
                              className="rounded-[var(--radius-sm)] p-1.5 text-[var(--ink-muted)] transition-colors hover:bg-[var(--surface)] hover:text-[var(--brass)]"
                            >
                              <Send size={14} />
                            </button>
                          )}
                          {(inv.status === "sent" || inv.status === "overdue") && (
                            <button
                              title="Mark paid"
                              onClick={() => setMarkPaidTarget(inv)}
                              className="rounded-[var(--radius-sm)] p-1.5 text-[var(--ink-muted)] transition-colors hover:bg-[var(--surface)] hover:text-[var(--verified)]"
                            >
                              <CheckCircle2 size={14} />
                            </button>
                          )}
                          {(inv.status === "draft" ||
                            inv.status === "sent" ||
                            inv.status === "overdue") && (
                            <button
                              title="Cancel"
                              onClick={() => cancelInvoice.mutate(inv.id)}
                              className="rounded-[var(--radius-sm)] p-1.5 text-[var(--ink-muted)] transition-colors hover:bg-[var(--surface)] hover:text-[var(--overdue)]"
                            >
                              <Ban size={14} />
                            </button>
                          )}
                          {inv.status === "draft" && (
                            <button
                              title="Delete"
                              onClick={() => {
                                if (confirm(`Delete draft invoice ${inv.invoice_number}?`)) {
                                  deleteInvoice.mutate(inv.id);
                                }
                              }}
                              className="rounded-[var(--radius-sm)] p-1.5 text-[var(--ink-muted)] transition-colors hover:bg-[var(--surface)] hover:text-[var(--overdue)]"
                            >
                              <Trash2 size={14} />
                            </button>
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

      <CreateInvoiceModal open={createOpen} onClose={() => setCreateOpen(false)} />
      <MarkPaidModal invoice={markPaidTarget} onClose={() => setMarkPaidTarget(null)} />
    </div>
  );
}
