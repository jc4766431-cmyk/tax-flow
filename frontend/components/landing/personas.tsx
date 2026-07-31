import type { LucideIcon } from "lucide-react";
import { User, Users, Building2 } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";

// Honest persona/segment cards, not fabricated customer quotes — TaxFlow
// has no customers yet, so no testimonials exist to show. See §0k.
const PERSONAS: { icon: LucideIcon; title: string; description: string }[] = [
  {
    icon: User,
    title: "Solo practitioner",
    description:
      "Running everything yourself — client documents over WhatsApp, filings in a spreadsheet, deadlines in your head. TaxFlow replaces the spreadsheet and the memory, not the WhatsApp habit.",
  },
  {
    icon: Users,
    title: "Small firm, 2-10 accountants",
    description:
      "Work is already split across people, but visibility isn't. A shared board means anyone can answer \"where's this filing?\" without pinging whoever owns it.",
  },
  {
    icon: Building2,
    title: "Growing firm, 11-50 accountants",
    description:
      "Enough clients that a missed deadline is a real risk, not a rare mistake. Firm-scoped data and a stamped history give you an audit trail, not just a task list.",
  },
];

export function Personas() {
  return (
    <section id="testimonials" className="mx-auto max-w-6xl px-6 py-20">
      <div className="max-w-xl">
        <p className="text-xs font-medium uppercase tracking-[0.18em] text-[var(--brass)]">
          Who it&apos;s for
        </p>
        <h2 className="mt-3 font-[family-name:var(--font-display)] text-3xl font-semibold tracking-tight text-[var(--ink)]">
          TaxFlow is new — here&apos;s who it&apos;s built for, not who&apos;s already using it.
        </h2>
        <p className="mt-4 text-base leading-relaxed text-[var(--ink-muted)]">
          We&apos;d rather tell you who this fits than invent quotes from
          clients we don&apos;t have yet.
        </p>
      </div>

      <div className="mt-12 grid grid-cols-1 gap-6 sm:grid-cols-3">
        {PERSONAS.map((persona) => (
          <Card key={persona.title}>
            <CardContent className="p-6">
              <persona.icon size={22} className="text-[var(--brass)]" />
              <p className="mt-4 font-[family-name:var(--font-display)] text-base font-semibold text-[var(--ink)]">
                {persona.title}
              </p>
              <p className="mt-2 text-sm leading-relaxed text-[var(--ink-muted)]">
                {persona.description}
              </p>
            </CardContent>
          </Card>
        ))}
      </div>
    </section>
  );
}
