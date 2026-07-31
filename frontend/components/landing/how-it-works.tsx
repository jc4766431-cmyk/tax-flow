const STEPS = [
  {
    title: "Add the client once",
    description:
      "Create their record with a PAN or GSTIN. From here on, routine requests go to them over WhatsApp — no separate login to hand out.",
  },
  {
    title: "Documents arrive, checked off automatically",
    description:
      "Each filing gets a six-item checklist. As documents come in — by upload or WhatsApp — the checklist updates itself against what's still missing.",
  },
  {
    title: "Work moves across the board",
    description:
      "Staff drag each filing through six stages — requested, documents uploaded, under review, approval required, filed, completed — so anyone can see where it stands.",
  },
  {
    title: "Every stage gets its stamp",
    description:
      "The client's own portal shows a dated, stamped timeline of exactly what happened and when — not just a status word.",
  },
];

export function HowItWorks() {
  return (
    <section id="how-it-works" className="border-y border-[var(--line)] bg-[var(--bg-elevated)]">
      <div className="mx-auto max-w-6xl px-6 py-20">
        <div className="max-w-xl">
          <p className="text-xs font-medium uppercase tracking-[0.18em] text-[var(--brass)]">
            How a filing moves
          </p>
          <h2 className="mt-3 font-[family-name:var(--font-display)] text-3xl font-semibold tracking-tight text-[var(--ink)]">
            Four steps, the same way every time.
          </h2>
        </div>

        <ol className="mt-12 grid grid-cols-1 gap-x-8 gap-y-10 sm:grid-cols-2">
          {STEPS.map((step, i) => (
            <li key={step.title} className="flex gap-4">
              <span className="tabular flex h-9 w-9 shrink-0 items-center justify-center rounded-full border border-[var(--line-strong)] text-sm font-medium text-[var(--brass)]">
                {String(i + 1).padStart(2, "0")}
              </span>
              <div>
                <p className="font-[family-name:var(--font-display)] text-base font-semibold text-[var(--ink)]">
                  {step.title}
                </p>
                <p className="mt-1.5 text-sm leading-relaxed text-[var(--ink-muted)]">
                  {step.description}
                </p>
              </div>
            </li>
          ))}
        </ol>
      </div>
    </section>
  );
}
