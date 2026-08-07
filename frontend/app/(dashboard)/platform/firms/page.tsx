"use client";

import { useState } from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { AxiosError } from "axios";
import { Building2, Plus, CreditCard } from "lucide-react";
import { api } from "@/lib/api";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Modal } from "@/components/dashboard/modal";
import { EmptyState } from "@/components/dashboard/empty-state";
import type { Firm } from "@/lib/types";

function errorMessage(err: unknown, fallback: string) {
  if (err instanceof AxiosError) {
    const detail = err.response?.data?.detail;
    if (typeof detail === "string") return detail;
  }
  return fallback;
}

function useFirms() {
  return useQuery<Firm[]>({
    queryKey: ["firms"],
    queryFn: async () => (await api.get("/firms")).data,
  });
}

function CreateFirmModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const queryClient = useQueryClient();
  const [name, setName] = useState("");
  const [legalName, setLegalName] = useState("");
  const [taxRegNumber, setTaxRegNumber] = useState("");
  const [address, setAddress] = useState("");

  function reset() {
    setName("");
    setLegalName("");
    setTaxRegNumber("");
    setAddress("");
  }

  const create = useMutation({
    mutationFn: async () =>
      (
        await api.post("/firms", {
          name,
          legal_name: legalName || null,
          tax_registration_number: taxRegNumber || null,
          address: address || null,
        })
      ).data,
    onSuccess: () => {
      toast.success(`${name} created`);
      queryClient.invalidateQueries({ queryKey: ["firms"] });
      reset();
      onClose();
    },
    onError: (err) => toast.error(errorMessage(err, "Couldn't create that firm.")),
  });

  return (
    <Modal open={open} onClose={onClose} title="Create a firm">
      <form
        onSubmit={(e) => {
          e.preventDefault();
          create.mutate();
        }}
        className="space-y-4"
      >
        <p className="text-sm text-[var(--ink-muted)]">
          This creates a bare firm record with no admin user attached. In most cases it&apos;s simpler
          to have the firm&apos;s partner sign up themselves at{" "}
          <span className="font-medium text-[var(--ink)]">/register-firm</span>, which creates the
          firm and their firm_admin account together. Use this only when you need to pre-provision
          a firm on someone&apos;s behalf.
        </p>
        <div>
          <Label htmlFor="firm-name">Firm name</Label>
          <Input id="firm-name" required value={name} onChange={(e) => setName(e.target.value)} />
        </div>
        <div>
          <Label htmlFor="firm-legal-name">Legal name</Label>
          <Input id="firm-legal-name" value={legalName} onChange={(e) => setLegalName(e.target.value)} />
        </div>
        <div>
          <Label htmlFor="firm-tax-reg">Tax registration number</Label>
          <Input id="firm-tax-reg" value={taxRegNumber} onChange={(e) => setTaxRegNumber(e.target.value)} />
        </div>
        <div>
          <Label htmlFor="firm-address">Address</Label>
          <Input id="firm-address" value={address} onChange={(e) => setAddress(e.target.value)} />
        </div>
        <div className="flex justify-end gap-2 pt-2">
          <Button type="button" variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" disabled={create.isPending || !name.trim()}>
            {create.isPending ? "Creating…" : "Create firm"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

export default function PlatformFirmsPage() {
  const { data: firms, isLoading, isError, error } = useFirms();
  const [modalOpen, setModalOpen] = useState(false);

  if (isError) throw error;

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="font-[family-name:var(--font-display)] text-2xl text-[var(--ink)]">Firms</h1>
          <p className="mt-1 text-sm text-[var(--ink-muted)]">
            Every firm on the TaxFlow platform.
          </p>
        </div>
        <Button onClick={() => setModalOpen(true)}>
          <Plus size={16} />
          New firm
        </Button>
      </div>

      <Card>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="space-y-3 p-5">
              {Array.from({ length: 4 }).map((_, i) => (
                <Skeleton key={i} className="h-10 w-full" />
              ))}
            </div>
          ) : !firms || firms.length === 0 ? (
            <div className="p-5">
              <EmptyState
                icon={Building2}
                title="No firms yet"
                description="Create the first firm, or have a partner sign up at /register-firm."
              />
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-t border-[var(--line)] text-left text-xs uppercase tracking-wide text-[var(--ink-muted)]">
                  <th className="px-5 py-3 font-medium">Name</th>
                  <th className="px-5 py-3 font-medium">Legal name</th>
                  <th className="px-5 py-3 font-medium">Tax registration</th>
                  <th className="px-5 py-3 font-medium">Status</th>
                  <th className="px-5 py-3 font-medium" />
                </tr>
              </thead>
              <tbody>
                {firms.map((firm) => (
                  <tr key={firm.id} className="border-t border-[var(--line)]">
                    <td className="px-5 py-3 text-[var(--ink)]">{firm.name}</td>
                    <td className="px-5 py-3 text-[var(--ink-muted)]">{firm.legal_name ?? "—"}</td>
                    <td className="px-5 py-3 text-[var(--ink-muted)]">{firm.tax_registration_number ?? "—"}</td>
                    <td className="px-5 py-3">
                      <Badge tone={firm.is_active ? "verified" : "neutral"}>
                        {firm.is_active ? "Active" : "Inactive"}
                      </Badge>
                    </td>
                    <td className="px-5 py-3 text-right">
                      <Link href={`/admin/billing?firm_id=${firm.id}`}>
                        <Button size="sm" variant="ghost">
                          <CreditCard size={14} />
                          Billing
                        </Button>
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </CardContent>
      </Card>

      <CreateFirmModal open={modalOpen} onClose={() => setModalOpen(false)} />
    </div>
  );
}
