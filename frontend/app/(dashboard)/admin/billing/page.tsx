"use client";

import { Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { AxiosError } from "axios";
import { CreditCard, History, Settings2, CheckCircle2 } from "lucide-react";
import { api } from "@/lib/api";
import { useCurrentUser } from "@/hooks/use-auth";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Modal } from "@/components/dashboard/modal";
import { cn } from "@/lib/utils";
import type {
  BillingPeriod,
  Firm,
  Plan,
  PlanTier,
  Subscription,
  SubscriptionStatus,
} from "@/lib/types";

function errorMessage(err: unknown, fallback: string) {
  if (err instanceof AxiosError) {
    const detail = err.response?.data?.detail;
    if (typeof detail === "string") return detail;
  }
  return fallback;
}

function statusTone(status: SubscriptionStatus): "verified" | "overdue" | "pending" | "neutral" {
  switch (status) {
    case "active":
      return "verified";
    case "past_due":
      return "overdue";
    case "trialing":
      return "pending";
    default:
      return "neutral";
  }
}

function formatPrice(plan: Plan) {
  if (plan.price_per_seat_inr == null) return "Custom pricing";
  return `₹${plan.price_per_seat_inr.toLocaleString("en-IN")} / seat / ${
    plan.billing_period === "annual" ? "year" : "month"
  }`;
}

// --- Data hooks -------------------------------------------------------

function useFirms(enabled: boolean) {
  return useQuery<Firm[]>({
    queryKey: ["firms"],
    queryFn: async () => (await api.get("/firms")).data,
    enabled,
  });
}

function usePlans() {
  return useQuery<Plan[]>({
    queryKey: ["billing", "plans"],
    queryFn: async () => (await api.get("/billing/plans", { params: { include_inactive: true } })).data,
  });
}

function useSubscription(firmId: string | undefined) {
  return useQuery<Subscription | null>({
    queryKey: ["billing", "subscription", firmId],
    queryFn: async () => {
      try {
        return (await api.get("/billing/subscription", { params: { firm_id: firmId } })).data;
      } catch (err) {
        if (err instanceof AxiosError && err.response?.status === 404) return null;
        throw err;
      }
    },
    enabled: !!firmId,
  });
}

function useSubscriptionHistory(firmId: string | undefined) {
  return useQuery<Subscription[]>({
    queryKey: ["billing", "subscription-history", firmId],
    queryFn: async () =>
      (await api.get("/billing/subscription/history", { params: { firm_id: firmId } })).data,
    enabled: !!firmId,
  });
}

// --- Plan catalog management (super_admin only) ------------------------

function PlanEditorModal({
  plan,
  open,
  onClose,
}: {
  plan: Plan | null;
  open: boolean;
  onClose: () => void;
}) {
  const queryClient = useQueryClient();
  const isNew = plan === null;

  // Keyed by plan id in the parent (see `key=` below), so this component
  // remounts — and these useState initializers re-run — whenever the
  // target plan changes, instead of syncing via an effect.
  const [tier, setTier] = useState<PlanTier>(plan?.tier ?? "free");
  const [name, setName] = useState(plan?.name ?? "");
  const [description, setDescription] = useState(plan?.description ?? "");
  const [price, setPrice] = useState(plan?.price_per_seat_inr != null ? String(plan.price_per_seat_inr) : "");
  const [billingPeriod, setBillingPeriod] = useState<BillingPeriod>(plan?.billing_period ?? "monthly");
  const [minSeats, setMinSeats] = useState(plan ? String(plan.min_seats) : "1");
  const [maxSeats, setMaxSeats] = useState(plan?.max_seats != null ? String(plan.max_seats) : "");
  const [maxClients, setMaxClients] = useState(plan?.max_clients != null ? String(plan.max_clients) : "");
  const [isActive, setIsActive] = useState(plan?.is_active ?? true);

  const save = useMutation({
    mutationFn: async () => {
      const body = {
        name,
        description: description || null,
        price_per_seat_inr: price ? Number(price) : null,
        billing_period: billingPeriod,
        min_seats: Number(minSeats) || 1,
        max_seats: maxSeats ? Number(maxSeats) : null,
        max_clients: maxClients ? Number(maxClients) : null,
        is_active: isActive,
      };
      if (isNew) {
        return (await api.post("/billing/plans", { ...body, tier })).data;
      }
      return (await api.patch(`/billing/plans/${plan!.id}`, body)).data;
    },
    onSuccess: () => {
      toast.success(isNew ? "Plan created" : "Plan updated");
      queryClient.invalidateQueries({ queryKey: ["billing", "plans"] });
      onClose();
    },
    onError: (err) => toast.error(errorMessage(err, "Couldn't save that plan.")),
  });

  return (
    <Modal open={open} onClose={onClose} title={isNew ? "New plan tier" : `Edit ${plan?.name}`}>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          save.mutate();
        }}
        className="space-y-4"
      >
        {isNew && (
          <div>
            <Label htmlFor="plan-tier">Tier</Label>
            <Select id="plan-tier" value={tier} onChange={(e) => setTier(e.target.value as PlanTier)}>
              <option value="free">Free</option>
              <option value="solo">Solo</option>
              <option value="team">Team</option>
              <option value="firm">Firm</option>
              <option value="enterprise">Enterprise</option>
            </Select>
          </div>
        )}
        <div>
          <Label htmlFor="plan-name">Display name</Label>
          <Input id="plan-name" required value={name} onChange={(e) => setName(e.target.value)} />
        </div>
        <div>
          <Label htmlFor="plan-description">Description</Label>
          <Input id="plan-description" value={description} onChange={(e) => setDescription(e.target.value)} />
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <Label htmlFor="plan-price">Price / seat (₹, blank = custom)</Label>
            <Input id="plan-price" inputMode="decimal" value={price} onChange={(e) => setPrice(e.target.value)} />
          </div>
          <div>
            <Label htmlFor="plan-period">Billing period</Label>
            <Select
              id="plan-period"
              value={billingPeriod}
              onChange={(e) => setBillingPeriod(e.target.value as BillingPeriod)}
            >
              <option value="monthly">Monthly</option>
              <option value="annual">Annual</option>
            </Select>
          </div>
        </div>
        <div className="grid grid-cols-3 gap-4">
          <div>
            <Label htmlFor="plan-min-seats">Min seats</Label>
            <Input id="plan-min-seats" inputMode="numeric" value={minSeats} onChange={(e) => setMinSeats(e.target.value)} />
          </div>
          <div>
            <Label htmlFor="plan-max-seats">Max seats</Label>
            <Input id="plan-max-seats" inputMode="numeric" value={maxSeats} onChange={(e) => setMaxSeats(e.target.value)} />
          </div>
          <div>
            <Label htmlFor="plan-max-clients">Max clients</Label>
            <Input id="plan-max-clients" inputMode="numeric" value={maxClients} onChange={(e) => setMaxClients(e.target.value)} />
          </div>
        </div>
        <label className="flex items-center gap-2 text-sm text-[var(--ink)]">
          <input type="checkbox" checked={isActive} onChange={(e) => setIsActive(e.target.checked)} />
          Active (sellable / visible to firms)
        </label>
        <div className="flex justify-end gap-2 pt-2">
          <Button type="button" variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" disabled={save.isPending || !name.trim()}>
            {save.isPending ? "Saving…" : isNew ? "Create plan" : "Save changes"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

function PlanCatalogManager({ plans }: { plans: Plan[] }) {
  const [editing, setEditing] = useState<Plan | null | undefined>(undefined);

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <div className="flex items-center gap-2">
          <Settings2 size={18} className="text-[var(--ink-muted)]" />
          <CardTitle>Plan catalog</CardTitle>
        </div>
        <Button size="sm" variant="secondary" onClick={() => setEditing(null)}>
          New plan
        </Button>
      </CardHeader>
      <CardContent className="p-0">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-t border-[var(--line)] text-left text-xs uppercase tracking-wide text-[var(--ink-muted)]">
              <th className="px-5 py-3 font-medium">Tier</th>
              <th className="px-5 py-3 font-medium">Name</th>
              <th className="px-5 py-3 font-medium">Price</th>
              <th className="px-5 py-3 font-medium">Seats</th>
              <th className="px-5 py-3 font-medium">Status</th>
              <th className="px-5 py-3 font-medium" />
            </tr>
          </thead>
          <tbody>
            {plans.map((plan) => (
              <tr key={plan.id} className="border-t border-[var(--line)]">
                <td className="px-5 py-3 capitalize text-[var(--ink)]">{plan.tier}</td>
                <td className="px-5 py-3 text-[var(--ink)]">{plan.name}</td>
                <td className="tabular px-5 py-3 text-[var(--ink-muted)]">{formatPrice(plan)}</td>
                <td className="tabular px-5 py-3 text-[var(--ink-muted)]">
                  {plan.min_seats}
                  {plan.max_seats ? `–${plan.max_seats}` : "+"}
                </td>
                <td className="px-5 py-3">
                  <Badge tone={plan.is_active ? "verified" : "neutral"}>
                    {plan.is_active ? "Active" : "Inactive"}
                  </Badge>
                </td>
                <td className="px-5 py-3 text-right">
                  <Button size="sm" variant="ghost" onClick={() => setEditing(plan)}>
                    Edit
                  </Button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </CardContent>
      <PlanEditorModal
        key={editing ? editing.id : "new"}
        plan={editing ?? null}
        open={editing !== undefined}
        onClose={() => setEditing(undefined)}
      />
    </Card>
  );
}

// --- Main page -----------------------------------------------------------

function BillingPageInner() {
  const { data: user } = useCurrentUser();
  const queryClient = useQueryClient();
  const isSuperAdmin = user?.role === "super_admin";
  const firmIdFromUrl = useSearchParams().get("firm_id");

  const { data: firms } = useFirms(!!isSuperAdmin);
  const [selectedFirmId, setSelectedFirmId] = useState<string>("");

  // Falls back to the URL's firm_id (set when arriving from Platform →
  // Firms) or the first firm in the list, without needing an effect to
  // sync that fallback into state.
  const effectiveFirmId = selectedFirmId || firmIdFromUrl || firms?.[0]?.id || "";

  const firmId = isSuperAdmin ? effectiveFirmId || undefined : user?.firm_id ?? undefined;

  const { data: plans, isLoading: plansLoading } = usePlans();
  const { data: subscription, isLoading: subLoading } = useSubscription(firmId);
  const { data: history } = useSubscriptionHistory(firmId);

  const [seats, setSeats] = useState("1");
  const [billingPeriod, setBillingPeriod] = useState<BillingPeriod>("monthly");

  const startSubscription = useMutation({
    mutationFn: async (planId: string) =>
      (
        await api.post("/billing/subscription", {
          plan_id: planId,
          seats: Number(seats) || 1,
          billing_period: billingPeriod,
          firm_id: isSuperAdmin ? firmId : undefined,
        })
      ).data,
    onSuccess: () => {
      toast.success("Subscription started");
      queryClient.invalidateQueries({ queryKey: ["billing", "subscription", firmId] });
      queryClient.invalidateQueries({ queryKey: ["billing", "subscription-history", firmId] });
    },
    onError: (err) => toast.error(errorMessage(err, "Couldn't start that subscription.")),
  });

  const switchPlan = useMutation({
    mutationFn: async (planId: string) =>
      (
        await api.patch(
          "/billing/subscription/upgrade",
          { plan_id: planId },
          { params: { firm_id: isSuperAdmin ? firmId : undefined } }
        )
      ).data,
    onSuccess: () => {
      toast.success("Plan updated");
      queryClient.invalidateQueries({ queryKey: ["billing", "subscription", firmId] });
    },
    onError: (err) => toast.error(errorMessage(err, "Couldn't switch plans.")),
  });

  const cancelSubscription = useMutation({
    mutationFn: async () =>
      (
        await api.post(
          "/billing/subscription/cancel",
          { at_period_end: true },
          { params: { firm_id: isSuperAdmin ? firmId : undefined } }
        )
      ).data,
    onSuccess: () => {
      toast.success("Subscription set to cancel at period end");
      queryClient.invalidateQueries({ queryKey: ["billing", "subscription", firmId] });
    },
    onError: (err) => toast.error(errorMessage(err, "Couldn't cancel that subscription.")),
  });

  if (isSuperAdmin && firms && firms.length === 0) {
    return (
      <div className="space-y-6">
        <h1 className="font-[family-name:var(--font-display)] text-2xl text-[var(--ink)]">Billing</h1>
        <p className="text-sm text-[var(--ink-muted)]">
          No firms exist yet — create one from Platform → Firms to manage its subscription.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="font-[family-name:var(--font-display)] text-2xl text-[var(--ink)]">Billing</h1>
          <p className="mt-1 text-sm text-[var(--ink-muted)]">
            {isSuperAdmin
              ? "Inspect and manage any firm's TaxFlow subscription."
              : "Your firm's TaxFlow subscription."}
          </p>
        </div>
        {isSuperAdmin && firms && firms.length > 0 && (
          <div className="w-full max-w-xs">
            <Label htmlFor="billing-firm">Firm</Label>
            <Select id="billing-firm" value={effectiveFirmId} onChange={(e) => setSelectedFirmId(e.target.value)}>
              {firms.map((f) => (
                <option key={f.id} value={f.id}>
                  {f.name}
                </option>
              ))}
            </Select>
          </div>
        )}
      </div>

      <Card>
        <CardHeader className="flex flex-row items-center gap-2">
          <CreditCard size={18} className="text-[var(--ink-muted)]" />
          <CardTitle>Current subscription</CardTitle>
        </CardHeader>
        <CardContent>
          {subLoading ? (
            <Skeleton className="h-20 w-full" />
          ) : !subscription ? (
            <p className="text-sm text-[var(--ink-muted)]">
              No active subscription. Choose a plan below to get started.
            </p>
          ) : (
            <div className="space-y-3">
              <div className="flex flex-wrap items-center gap-3">
                <span className="font-[family-name:var(--font-display)] text-lg text-[var(--ink)]">
                  {subscription.plan.name}
                </span>
                <Badge tone={statusTone(subscription.status)}>{subscription.status.replace("_", " ")}</Badge>
                {subscription.cancel_at_period_end && <Badge tone="overdue">Cancels at period end</Badge>}
              </div>
              <div className="grid grid-cols-2 gap-4 text-sm sm:grid-cols-4">
                <div>
                  <p className="text-xs uppercase tracking-wide text-[var(--ink-muted)]">Seats</p>
                  <p className="tabular text-[var(--ink)]">{subscription.seats}</p>
                </div>
                <div>
                  <p className="text-xs uppercase tracking-wide text-[var(--ink-muted)]">Period</p>
                  <p className="text-[var(--ink)] capitalize">{subscription.billing_period}</p>
                </div>
                <div>
                  <p className="text-xs uppercase tracking-wide text-[var(--ink-muted)]">Current period</p>
                  <p className="tabular text-[var(--ink)]">
                    {subscription.current_period_start} – {subscription.current_period_end}
                  </p>
                </div>
                {subscription.payment_gateway_ref && (
                  <div>
                    <p className="text-xs uppercase tracking-wide text-[var(--ink-muted)]">Payment ref</p>
                    <p className="tabular truncate text-[var(--ink)]" title={subscription.payment_gateway_ref}>
                      {subscription.payment_gateway_ref}
                    </p>
                  </div>
                )}
              </div>
              {subscription.status === "trialing" && subscription.payment_gateway_ref && (
                <p className="text-xs text-[var(--ink-muted)]">
                  Awaiting payment confirmation for this order before the plan activates.
                </p>
              )}
              {!subscription.cancel_at_period_end && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => cancelSubscription.mutate()}
                  disabled={cancelSubscription.isPending}
                >
                  {cancelSubscription.isPending ? "Cancelling…" : "Cancel at period end"}
                </Button>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Plans</CardTitle>
        </CardHeader>
        <CardContent>
          {plansLoading || !plans ? (
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
              {Array.from({ length: 3 }).map((_, i) => (
                <Skeleton key={i} className="h-40 w-full" />
              ))}
            </div>
          ) : (
            <>
              {!subscription && (
                <div className="mb-4 grid grid-cols-2 gap-4 sm:max-w-sm">
                  <div>
                    <Label htmlFor="new-sub-seats">Seats</Label>
                    <Input
                      id="new-sub-seats"
                      inputMode="numeric"
                      value={seats}
                      onChange={(e) => setSeats(e.target.value)}
                    />
                  </div>
                  <div>
                    <Label htmlFor="new-sub-period">Billing period</Label>
                    <Select
                      id="new-sub-period"
                      value={billingPeriod}
                      onChange={(e) => setBillingPeriod(e.target.value as BillingPeriod)}
                    >
                      <option value="monthly">Monthly</option>
                      <option value="annual">Annual</option>
                    </Select>
                  </div>
                </div>
              )}
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
                {plans
                  .filter((p) => p.is_active || p.id === subscription?.plan_id)
                  .map((plan) => {
                    const isCurrent = subscription?.plan_id === plan.id;
                    return (
                      <div
                        key={plan.id}
                        className={cn(
                          "flex flex-col justify-between gap-4 rounded-[var(--radius-md)] border p-4",
                          isCurrent ? "border-[var(--brass)]" : "border-[var(--line)]"
                        )}
                      >
                        <div>
                          <div className="flex items-center justify-between">
                            <p className="font-[family-name:var(--font-display)] text-base text-[var(--ink)]">
                              {plan.name}
                            </p>
                            {isCurrent && <CheckCircle2 size={16} className="text-[var(--brass)]" />}
                          </div>
                          {plan.description && (
                            <p className="mt-1 text-sm text-[var(--ink-muted)]">{plan.description}</p>
                          )}
                          <p className="tabular mt-3 text-sm text-[var(--ink)]">{formatPrice(plan)}</p>
                          <p className="mt-1 text-xs text-[var(--ink-muted)]">
                            {plan.min_seats}
                            {plan.max_seats ? `–${plan.max_seats}` : "+"} seats
                            {plan.max_clients ? ` · up to ${plan.max_clients} clients` : ""}
                          </p>
                        </div>
                        {isCurrent ? (
                          <Button size="sm" variant="secondary" disabled>
                            Current plan
                          </Button>
                        ) : subscription ? (
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => switchPlan.mutate(plan.id)}
                            disabled={switchPlan.isPending || plan.tier === "enterprise"}
                          >
                            {switchPlan.isPending ? "Switching…" : "Switch to this plan"}
                          </Button>
                        ) : (
                          <Button
                            size="sm"
                            onClick={() => startSubscription.mutate(plan.id)}
                            disabled={startSubscription.isPending || plan.tier === "enterprise"}
                          >
                            {startSubscription.isPending ? "Starting…" : "Subscribe"}
                          </Button>
                        )}
                      </div>
                    );
                  })}
              </div>
            </>
          )}
        </CardContent>
      </Card>

      {history && history.length > 0 && (
        <Card>
          <CardHeader className="flex flex-row items-center gap-2">
            <History size={18} className="text-[var(--ink-muted)]" />
            <CardTitle>History</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-t border-[var(--line)] text-left text-xs uppercase tracking-wide text-[var(--ink-muted)]">
                  <th className="px-5 py-3 font-medium">Plan</th>
                  <th className="px-5 py-3 font-medium">Status</th>
                  <th className="px-5 py-3 font-medium">Period</th>
                </tr>
              </thead>
              <tbody>
                {history.map((s) => (
                  <tr key={s.id} className="border-t border-[var(--line)]">
                    <td className="px-5 py-3 text-[var(--ink)]">{s.plan.name}</td>
                    <td className="px-5 py-3">
                      <Badge tone={statusTone(s.status)}>{s.status.replace("_", " ")}</Badge>
                    </td>
                    <td className="tabular px-5 py-3 text-[var(--ink-muted)]">
                      {s.current_period_start} – {s.current_period_end}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </CardContent>
        </Card>
      )}

      {isSuperAdmin && plans && <PlanCatalogManager plans={plans} />}
    </div>
  );
}

export default function BillingPage() {
  return (
    <Suspense fallback={null}>
      <BillingPageInner />
    </Suspense>
  );
}
