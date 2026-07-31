import Link from "next/link";
import { Check } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

// Copy matches backend/scripts/seed_plans.py exactly — do not change the
// numbers here without updating that script (and STRATEGY_REVIEW.md
// Phase 7) too.
const TIERS = [
  {
    name: "Free",
    price: "₹0",
    unit: "1 seat",
    description: "Try TaxFlow with up to 5 clients.",
    features: ["1 seat", "Up to 5 clients", "No automation"],
    cta: "Get started free",
    featured: false,
  },
  {
    name: "Solo",
    price: "₹999",
    unit: "/month",
    description: "For a single practitioner.",
    features: ["1 seat", "Unlimited clients", "Flat monthly price"],
    cta: "Get started",
    featured: false,
  },
  {
    name: "Team",
    price: "₹1,499",
    unit: "/user/month",
    description: "For small firms of 2-10 accountants.",
    features: ["2-10 seats", "Unlimited clients", "No annual lock-in"],
    cta: "Get started",
    featured: true,
  },
  {
    name: "Firm",
    price: "₹1,999",
    unit: "/user/month",
    description: "For firms of 11-50 accountants.",
    features: ["11-50 seats", "Unlimited clients", "Compliance add-on available"],
    cta: "Get started",
    featured: false,
  },
  {
    name: "Enterprise",
    price: "Custom",
    unit: "51+ seats",
    description: "Multi-branch firms, white-label portal.",
    features: ["51+ seats", "White-label client portal", "Dedicated onboarding"],
    cta: "Contact us",
    featured: false,
  },
];

export function Pricing() {
  return (
    <section id="pricing" className="border-y border-[var(--line)] bg-[var(--bg-elevated)]">
      <div className="mx-auto max-w-6xl px-6 py-20">
        <div className="max-w-xl">
          <p className="text-xs font-medium uppercase tracking-[0.18em] text-[var(--brass)]">
            Pricing
          </p>
          <h2 className="mt-3 font-[family-name:var(--font-display)] text-3xl font-semibold tracking-tight text-[var(--ink)]">
            Priced per seat, not per client.
          </h2>
        </div>

        <div className="mt-12 grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-5">
          {TIERS.map((tier) => (
            <Card
              key={tier.name}
              className={tier.featured ? "border-[var(--brass)]" : undefined}
            >
              <CardContent className="flex h-full flex-col p-6">
                <p className="font-[family-name:var(--font-display)] text-base font-semibold text-[var(--ink)]">
                  {tier.name}
                </p>
                <p className="mt-3">
                  <span className="tabular font-[family-name:var(--font-display)] text-2xl font-semibold text-[var(--ink)]">
                    {tier.price}
                  </span>
                  <span className="ml-1 text-xs text-[var(--ink-faint)]">{tier.unit}</span>
                </p>
                <p className="mt-2 text-sm text-[var(--ink-muted)]">{tier.description}</p>
                <ul className="mt-4 flex-1 space-y-2">
                  {tier.features.map((f) => (
                    <li key={f} className="flex items-start gap-2 text-xs text-[var(--ink-muted)]">
                      <Check size={14} className="mt-0.5 shrink-0 text-[var(--brass)]" />
                      {f}
                    </li>
                  ))}
                </ul>
                <Link href="/register" className="mt-6 block">
                  <Button
                    variant={tier.featured ? "primary" : "outline"}
                    size="sm"
                    className="w-full"
                  >
                    {tier.cta}
                  </Button>
                </Link>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </section>
  );
}
