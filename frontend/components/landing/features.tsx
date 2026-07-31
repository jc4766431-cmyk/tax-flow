import type { LucideIcon } from "lucide-react";
import {
  MessageCircle,
  ListChecks,
  LayoutGrid,
  CalendarClock,
  ShieldCheck,
  Stamp,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";

const FEATURES: { icon: LucideIcon; title: string; description: string }[] = [
  {
    icon: MessageCircle,
    title: "WhatsApp-first for clients",
    description:
      "Clients send documents and get status updates over WhatsApp — no app to install, no password to remember.",
  },
  {
    icon: ListChecks,
    title: "Document checklists that track themselves",
    description:
      "Every filing gets a six-item checklist — PAN, Aadhaar, GST report, salary slip, investment proof, bank statement — and updates itself as documents land.",
  },
  {
    icon: LayoutGrid,
    title: "A board your whole firm works from",
    description:
      "Requested, documents uploaded, under review, approval required, filed, completed — one board, six stages, every filing visible at a glance.",
  },
  {
    icon: CalendarClock,
    title: "Deadlines that surface themselves",
    description:
      "Overdue filings and the next 14 days of due dates sit on the firm overview — nobody has to go looking for what's late.",
  },
  {
    icon: ShieldCheck,
    title: "One firm's data, one firm's eyes",
    description:
      "Every client, document, and filing is scoped to the firm that owns it — accountants at one firm can't see another firm's records.",
  },
  {
    icon: Stamp,
    title: "A stamped, dated history",
    description:
      "Every stage a filing passes through is timestamped and kept — a real record for the client, not just a status label.",
  },
];

export function Features() {
  return (
    <section id="features" className="mx-auto max-w-6xl px-6 py-20">
      <div className="max-w-xl">
        <p className="text-xs font-medium uppercase tracking-[0.18em] text-[var(--brass)]">
          What&apos;s in the ledger
        </p>
        <h2 className="mt-3 font-[family-name:var(--font-display)] text-3xl font-semibold tracking-tight text-[var(--ink)]">
          Everything a practice already does, kept in one record.
        </h2>
      </div>

      <div className="mt-10 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {FEATURES.map((feature) => (
          <Card key={feature.title}>
            <CardContent className="p-5">
              <div className="flex h-9 w-9 items-center justify-center rounded-[var(--radius-sm)] bg-[var(--brass)]/15 text-[var(--brass)]">
                <feature.icon size={18} />
              </div>
              <p className="mt-4 font-[family-name:var(--font-display)] text-base font-semibold text-[var(--ink)]">
                {feature.title}
              </p>
              <p className="mt-2 text-sm leading-relaxed text-[var(--ink-muted)]">
                {feature.description}
              </p>
            </CardContent>
          </Card>
        ))}
      </div>
    </section>
  );
}
