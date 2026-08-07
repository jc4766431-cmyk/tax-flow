"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { AxiosError } from "axios";
import { UserPlus, ClipboardCheck } from "lucide-react";
import { api } from "@/lib/api";
import { Modal } from "@/components/dashboard/modal";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import type { StaffMember } from "@/lib/types";

function errorMessage(err: unknown, fallback: string) {
  if (err instanceof AxiosError) {
    const detail = err.response?.data?.detail;
    if (typeof detail === "string") return detail;
  }
  return fallback;
}

// Client-role users who've accepted their invite but don't have a Client
// profile (company_name/PAN/GSTIN) yet — see backend GET /users/pending-clients.
function usePendingClientProfiles(firmId: string | undefined) {
  return useQuery<StaffMember[]>({
    queryKey: ["users", "pending-clients", firmId],
    queryFn: async () =>
      (await api.get("/users/pending-clients", { params: { firm_id: firmId } })).data,
    enabled: !!firmId,
  });
}

function useStaffForAssignment(firmId: string | undefined) {
  return useQuery<StaffMember[]>({
    queryKey: ["users", firmId],
    queryFn: async () => (await api.get("/users", { params: { firm_id: firmId } })).data,
    enabled: !!firmId,
  });
}

type Tab = "invite" | "complete";

export function AddClientModal({
  open,
  onClose,
  firmId,
}: {
  open: boolean;
  onClose: () => void;
  firmId: string | undefined;
}) {
  const [tab, setTab] = useState<Tab>("invite");

  return (
    <Modal open={open} onClose={onClose} title="Add client">
      <div className="mb-5 flex gap-1 rounded-[var(--radius-sm)] bg-[var(--surface)] p-1">
        <button
          type="button"
          onClick={() => setTab("invite")}
          className={`flex-1 rounded-[var(--radius-sm)] px-3 py-1.5 text-sm font-medium transition-colors ${
            tab === "invite"
              ? "bg-[var(--bg-elevated)] text-[var(--ink)] shadow-sm"
              : "text-[var(--ink-muted)]"
          }`}
        >
          Invite new client
        </button>
        <button
          type="button"
          onClick={() => setTab("complete")}
          className={`flex-1 rounded-[var(--radius-sm)] px-3 py-1.5 text-sm font-medium transition-colors ${
            tab === "complete"
              ? "bg-[var(--bg-elevated)] text-[var(--ink)] shadow-sm"
              : "text-[var(--ink-muted)]"
          }`}
        >
          Complete a profile
        </button>
      </div>

      {tab === "invite" ? (
        <InviteClientTab firmId={firmId} onSent={() => setTab("complete")} />
      ) : (
        <CompleteProfileTab firmId={firmId} onDone={onClose} />
      )}
    </Modal>
  );
}

function InviteClientTab({
  firmId,
  onSent,
}: {
  firmId: string | undefined;
  onSent: () => void;
}) {
  const [email, setEmail] = useState("");

  const sendInvite = useMutation({
    mutationFn: async () =>
      (
        await api.post("/invites", {
          email,
          role: "client",
          firm_id: firmId,
        })
      ).data,
    onSuccess: () => {
      toast.success(`Invite sent to ${email}`);
      setEmail("");
      onSent();
    },
    onError: (err) => toast.error(errorMessage(err, "Couldn't send that invite.")),
  });

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        if (email.trim() && firmId) sendInvite.mutate();
      }}
      className="space-y-4"
    >
      <div className="flex items-start gap-2 rounded-[var(--radius-sm)] border border-[var(--line)] bg-[var(--surface)] p-3 text-xs text-[var(--ink-muted)]">
        <UserPlus size={14} className="mt-0.5 shrink-0" />
        <p>
          This sends the client an account invite. Once they accept it, switch to
          &quot;Complete a profile&quot; to add their company details and finish setting them up.
        </p>
      </div>
      <div>
        <Label htmlFor="client-invite-email">Client email</Label>
        <Input
          id="client-invite-email"
          type="email"
          required
          placeholder="client@company.com"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
      </div>
      <Button type="submit" disabled={sendInvite.isPending || !email.trim()} className="w-full">
        {sendInvite.isPending ? "Sending…" : "Send invite"}
      </Button>
    </form>
  );
}

function CompleteProfileTab({
  firmId,
  onDone,
}: {
  firmId: string | undefined;
  onDone: () => void;
}) {
  const queryClient = useQueryClient();
  const { data: pending, isLoading } = usePendingClientProfiles(firmId);
  const { data: staff } = useStaffForAssignment(firmId);
  const [selectedUserId, setSelectedUserId] = useState<string>("");

  const [companyName, setCompanyName] = useState("");
  const [panNumber, setPanNumber] = useState("");
  const [gstin, setGstin] = useState("");
  const [accountantId, setAccountantId] = useState("");

  const selectedUser = pending?.find((u) => u.id === selectedUserId);

  const createClient = useMutation({
    mutationFn: async () =>
      (
        await api.post("/clients", {
          user_id: selectedUserId,
          firm_id: firmId,
          company_name: companyName || null,
          pan_number: panNumber || null,
          gstin: gstin || null,
          assigned_accountant_id: accountantId || null,
        })
      ).data,
    onSuccess: () => {
      toast.success(`${companyName || selectedUser?.email} added as a client`);
      queryClient.invalidateQueries({ queryKey: ["clients"] });
      queryClient.invalidateQueries({ queryKey: ["users", "pending-clients", firmId] });
      onDone();
    },
    onError: (err) => toast.error(errorMessage(err, "Couldn't create that client.")),
  });

  if (isLoading) {
    return (
      <div className="space-y-3">
        {Array.from({ length: 3 }).map((_, i) => (
          <Skeleton key={i} className="h-10 w-full" />
        ))}
      </div>
    );
  }

  if (!pending || pending.length === 0) {
    return (
      <div className="flex items-start gap-2 rounded-[var(--radius-sm)] border border-[var(--line)] bg-[var(--surface)] p-4 text-sm text-[var(--ink-muted)]">
        <ClipboardCheck size={16} className="mt-0.5 shrink-0" />
        <p>
          No accepted client invites are waiting on a profile yet. Once someone accepts a
          client invite, they&apos;ll show up here.
        </p>
      </div>
    );
  }

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        if (selectedUserId && firmId) createClient.mutate();
      }}
      className="space-y-4"
    >
      <div>
        <Label htmlFor="pending-client">Accepted invite</Label>
        <Select
          id="pending-client"
          value={selectedUserId}
          onChange={(e) => setSelectedUserId(e.target.value)}
          required
        >
          <option value="" disabled>
            Select a person…
          </option>
          {pending.map((u) => (
            <option key={u.id} value={u.id}>
              {u.full_name} — {u.email}
            </option>
          ))}
        </Select>
      </div>
      <div>
        <Label htmlFor="company-name">Company name</Label>
        <Input
          id="company-name"
          value={companyName}
          onChange={(e) => setCompanyName(e.target.value)}
          placeholder="Acme Pvt Ltd"
        />
      </div>
      <div className="grid grid-cols-2 gap-4">
        <div>
          <Label htmlFor="pan-number">PAN</Label>
          <Input
            id="pan-number"
            value={panNumber}
            onChange={(e) => setPanNumber(e.target.value.toUpperCase())}
            placeholder="ABCDE1234F"
          />
        </div>
        <div>
          <Label htmlFor="gstin">GSTIN</Label>
          <Input
            id="gstin"
            value={gstin}
            onChange={(e) => setGstin(e.target.value.toUpperCase())}
            placeholder="22ABCDE1234F1Z5"
          />
        </div>
      </div>
      <div>
        <Label htmlFor="accountant">Assigned accountant (optional)</Label>
        <Select id="accountant" value={accountantId} onChange={(e) => setAccountantId(e.target.value)}>
          <option value="">Unassigned</option>
          {(staff ?? [])
            .filter((s) => s.role !== "client")
            .map((s) => (
              <option key={s.id} value={s.id}>
                {s.full_name} ({s.role.replace("_", " ")})
              </option>
            ))}
        </Select>
      </div>
      <Button type="submit" disabled={createClient.isPending || !selectedUserId} className="w-full">
        {createClient.isPending ? "Creating…" : "Create client"}
      </Button>
    </form>
  );
}
