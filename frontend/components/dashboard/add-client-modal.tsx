"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { AxiosError } from "axios";
import { MessageCircle } from "lucide-react";
import { api } from "@/lib/api";
import { Modal } from "@/components/dashboard/modal";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

function errorMessage(err: unknown, fallback: string) {
  if (err instanceof AxiosError) {
    const detail = err.response?.data?.detail;
    if (typeof detail === "string") return detail;
  }
  return fallback;
}

// Quick-add is the only client-onboarding path — client-invite-first
// onboarding was retired in favor of this. Staff can still grant an
// already-added client web-portal access later from their client page.
export function AddClientModal({
  open,
  onClose,
  firmId,
}: {
  open: boolean;
  onClose: () => void;
  firmId: string | undefined;
}) {
  const queryClient = useQueryClient();
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [companyName, setCompanyName] = useState("");
  const [panNumber, setPanNumber] = useState("");
  const [gstin, setGstin] = useState("");

  const quickAdd = useMutation({
    mutationFn: async () =>
      (
        await api.post("/clients/quick-add", {
          name,
          phone,
          company_name: companyName || null,
          pan_number: panNumber || null,
          gstin: gstin || null,
        })
      ).data,
    onSuccess: () => {
      toast.success(`${name} added — a WhatsApp document request was just sent`);
      queryClient.invalidateQueries({ queryKey: ["clients"] });
      setName("");
      setPhone("");
      setCompanyName("");
      setPanNumber("");
      setGstin("");
      onClose();
    },
    onError: (err) => toast.error(errorMessage(err, "Couldn't add that client.")),
  });

  return (
    <Modal open={open} onClose={onClose} title="Add client">
      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (name.trim() && phone.trim()) quickAdd.mutate();
        }}
        className="space-y-4"
      >
        <div className="flex items-start gap-2 rounded-[var(--radius-sm)] border border-[var(--line)] bg-[var(--surface)] p-3 text-xs text-[var(--ink-muted)]">
          <MessageCircle size={14} className="mt-0.5 shrink-0" />
          <p>
            Adds the client instantly — no account or login needed yet. We&apos;ll message them on
            WhatsApp right away asking for their first documents. You can invite them to the web
            portal later from their client page.
          </p>
        </div>
        <div>
          <Label htmlFor="quick-add-name">Name</Label>
          <Input
            id="quick-add-name"
            required
            placeholder="Priya Sharma"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
        </div>
        <div>
          <Label htmlFor="quick-add-phone">WhatsApp / phone number</Label>
          <Input
            id="quick-add-phone"
            type="tel"
            required
            placeholder="98765 43210"
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
          />
        </div>
        <div>
          <Label htmlFor="quick-add-company">Company name (optional)</Label>
          <Input
            id="quick-add-company"
            value={companyName}
            onChange={(e) => setCompanyName(e.target.value)}
            placeholder="Acme Pvt Ltd"
          />
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <Label htmlFor="quick-add-pan">PAN (optional)</Label>
            <Input
              id="quick-add-pan"
              value={panNumber}
              onChange={(e) => setPanNumber(e.target.value.toUpperCase())}
              placeholder="ABCDE1234F"
            />
          </div>
          <div>
            <Label htmlFor="quick-add-gstin">GSTIN (optional)</Label>
            <Input
              id="quick-add-gstin"
              value={gstin}
              onChange={(e) => setGstin(e.target.value.toUpperCase())}
              placeholder="22ABCDE1234F1Z5"
            />
          </div>
        </div>
        <Button
          type="submit"
          disabled={quickAdd.isPending || !name.trim() || !phone.trim() || !firmId}
          className="w-full"
        >
          {quickAdd.isPending ? "Adding…" : "Add client & message on WhatsApp"}
        </Button>
      </form>
    </Modal>
  );
}
