"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { AxiosError } from "axios";
import { UserPlus, Mail, Clock, CheckCircle2, XCircle, Users } from "lucide-react";
import { api } from "@/lib/api";
import { useCurrentUser } from "@/hooks/use-auth";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/dashboard/empty-state";
import type { Invite, StaffMember, StaffRole } from "@/lib/types";

const ROLE_OPTIONS: { value: StaffRole; label: string; blurb: string }[] = [
  { value: "accountant", label: "Accountant", blurb: "Works filings, gets clients assigned to them." },
  { value: "reviewer", label: "Reviewer", blurb: "Reviews and approves completed work." },
  { value: "firm_admin", label: "Firm admin", blurb: "Full access — can manage staff, billing, and clients." },
];

function errorMessage(err: unknown, fallback: string) {
  if (err instanceof AxiosError) {
    const detail = err.response?.data?.detail;
    if (typeof detail === "string") return detail;
  }
  return fallback;
}

function roleLabel(role: string) {
  return role.replace("_", " ");
}

function useInvites(firmId: string | undefined) {
  return useQuery<Invite[]>({
    queryKey: ["invites", firmId],
    queryFn: async () => (await api.get("/invites", { params: { firm_id: firmId } })).data,
    enabled: !!firmId,
  });
}

function useStaff(firmId: string | undefined) {
  return useQuery<StaffMember[]>({
    queryKey: ["users", firmId],
    queryFn: async () => (await api.get("/users", { params: { firm_id: firmId } })).data,
    enabled: !!firmId,
  });
}

function inviteStatus(invite: Invite): { label: string; tone: "verified" | "overdue" | "pending" } {
  if (invite.accepted_at) return { label: "Accepted", tone: "verified" };
  if (new Date(invite.expires_at) < new Date()) return { label: "Expired", tone: "overdue" };
  return { label: "Pending", tone: "pending" };
}

function InviteStatusIcon({ tone }: { tone: "verified" | "overdue" | "pending" }) {
  if (tone === "verified") return <CheckCircle2 size={14} />;
  if (tone === "overdue") return <XCircle size={14} />;
  return <Clock size={14} />;
}

export default function TeamPage() {
  const { data: user } = useCurrentUser();
  const queryClient = useQueryClient();

  const [email, setEmail] = useState("");
  const [role, setRole] = useState<StaffRole>("accountant");

  // super_admin has no firm_id of their own — team management is scoped to
  // a firm, so a super_admin manages team from the Platform → Firms page
  // instead (there's no "own firm" for a platform-level user).
  const firmId = user?.firm_id ?? undefined;

  const { data: staff, isLoading: staffLoading } = useStaff(firmId);
  const { data: invites, isLoading } = useInvites(firmId);

  const sendInvite = useMutation({
    mutationFn: async () =>
      (
        await api.post("/invites", {
          email,
          role,
          firm_id: firmId,
        })
      ).data,
    onSuccess: () => {
      toast.success(`Invite sent to ${email}`);
      setEmail("");
      queryClient.invalidateQueries({ queryKey: ["invites", firmId] });
    },
    onError: (err) => toast.error(errorMessage(err, "Couldn't send that invite.")),
  });

  if (user && user.role === "super_admin") {
    return (
      <div className="space-y-6">
        <h1 className="font-[family-name:var(--font-display)] text-2xl text-[var(--ink)]">Team</h1>
        <EmptyState
          icon={Users}
          title="No firm of your own"
          description="Team invites are firm-scoped. To manage a firm&apos;s staff, open that firm from Platform → Firms."
        />
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="font-[family-name:var(--font-display)] text-2xl text-[var(--ink)]">Team</h1>
        <p className="mt-1 text-sm text-[var(--ink-muted)]">
          Invite partners and staff to your firm&apos;s TaxFlow workspace.
        </p>
      </div>

      <Card>
        <CardHeader className="flex flex-row items-center gap-2">
          <UserPlus size={18} className="text-[var(--ink-muted)]" />
          <CardTitle>Invite a colleague</CardTitle>
        </CardHeader>
        <CardContent>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              if (email.trim()) sendInvite.mutate();
            }}
            className="grid grid-cols-1 gap-4 sm:grid-cols-[2fr_1.4fr_auto] sm:items-end"
          >
            <div>
              <Label htmlFor="invite-email">Email</Label>
              <Input
                id="invite-email"
                type="email"
                required
                placeholder="colleague@firm.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </div>
            <div>
              <Label htmlFor="invite-role">Role</Label>
              <Select id="invite-role" value={role} onChange={(e) => setRole(e.target.value as StaffRole)}>
                {ROLE_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </Select>
            </div>
            <Button type="submit" disabled={sendInvite.isPending || !email.trim()}>
              {sendInvite.isPending ? "Sending…" : "Send invite"}
            </Button>
          </form>
          <p className="mt-3 text-xs text-[var(--ink-muted)]">
            {ROLE_OPTIONS.find((o) => o.value === role)?.blurb} Invites expire after 7 days.
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-center gap-2">
          <Users size={18} className="text-[var(--ink-muted)]" />
          <CardTitle>Current staff</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {staffLoading ? (
            <div className="space-y-3 p-5">
              {Array.from({ length: 3 }).map((_, i) => (
                <Skeleton key={i} className="h-10 w-full" />
              ))}
            </div>
          ) : !staff || staff.length === 0 ? (
            <div className="p-5">
              <EmptyState
                icon={Users}
                title="No staff yet"
                description="Staff who accept an invite will show up here."
              />
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-t border-[var(--line)] text-left text-xs uppercase tracking-wide text-[var(--ink-muted)]">
                  <th className="px-5 py-3 font-medium">Name</th>
                  <th className="px-5 py-3 font-medium">Email</th>
                  <th className="px-5 py-3 font-medium">Role</th>
                  <th className="px-5 py-3 font-medium">Status</th>
                </tr>
              </thead>
              <tbody>
                {staff.map((member) => (
                  <tr key={member.id} className="border-t border-[var(--line)]">
                    <td className="px-5 py-3 text-[var(--ink)]">{member.full_name}</td>
                    <td className="px-5 py-3 text-[var(--ink)]">{member.email}</td>
                    <td className="px-5 py-3">
                      <Badge tone={member.role === "firm_admin" || member.role === "super_admin" ? "brass" : "neutral"}>
                        {roleLabel(member.role)}
                      </Badge>
                    </td>
                    <td className="px-5 py-3">
                      <Badge tone={member.is_active ? "verified" : "neutral"}>
                        {member.is_active ? "Active" : "Inactive"}
                      </Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-center gap-2">
          <Mail size={18} className="text-[var(--ink-muted)]" />
          <CardTitle>Invites</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="space-y-3 p-5">
              {Array.from({ length: 3 }).map((_, i) => (
                <Skeleton key={i} className="h-10 w-full" />
              ))}
            </div>
          ) : !invites || invites.length === 0 ? (
            <div className="p-5">
              <EmptyState
                icon={Mail}
                title="No invites yet"
                description="Invites you send will show up here with their status."
              />
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-t border-[var(--line)] text-left text-xs uppercase tracking-wide text-[var(--ink-muted)]">
                  <th className="px-5 py-3 font-medium">Email</th>
                  <th className="px-5 py-3 font-medium">Role</th>
                  <th className="px-5 py-3 font-medium">Status</th>
                  <th className="px-5 py-3 font-medium">Sent</th>
                  <th className="px-5 py-3 font-medium">Expires</th>
                </tr>
              </thead>
              <tbody>
                {invites.map((invite) => {
                  const status = inviteStatus(invite);
                  return (
                    <tr key={invite.id} className="border-t border-[var(--line)]">
                      <td className="px-5 py-3 text-[var(--ink)]">{invite.email}</td>
                      <td className="px-5 py-3 text-[var(--ink)]">{roleLabel(invite.role)}</td>
                      <td className="px-5 py-3">
                        <Badge tone={status.tone}>
                          <InviteStatusIcon tone={status.tone} />
                          {status.label}
                        </Badge>
                      </td>
                      <td className="tabular px-5 py-3 text-[var(--ink-muted)]">
                        {new Date(invite.created_at).toLocaleDateString()}
                      </td>
                      <td className="tabular px-5 py-3 text-[var(--ink-muted)]">
                        {new Date(invite.expires_at).toLocaleDateString()}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
