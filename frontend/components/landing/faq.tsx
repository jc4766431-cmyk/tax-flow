"use client";

import { useState } from "react";
import { ChevronDown } from "lucide-react";

// Plain useState-based disclosure, no radix accordion — per NEXT-PROMPT.md.
const FAQS = [
  {
    q: "Do my clients need to install an app?",
    a: "No. Clients send documents and get status updates over WhatsApp, the way they already message you. A client portal login exists for anyone who wants one, but it's optional.",
  },
  {
    q: "What happens after the Free plan's 5 clients?",
    a: "You can upgrade to Solo, Team, or Firm at any point — pricing is per seat, not per client, so client count above 5 only matters on the Free tier.",
  },
  {
    q: "Is there an annual lock-in?",
    a: "No. Team and Firm plans bill monthly with no annual-only pricing required.",
  },
  {
    q: "Can two firms see each other's clients?",
    a: "No. Every client, document, and filing is scoped to the firm that owns it — accountants at one firm can't see another firm's records.",
  },
  {
    q: "What does Enterprise include?",
    a: "Custom pricing for 51+ seats or multi-branch firms, including a white-label client portal and dedicated onboarding. There's no self-serve checkout for this tier — contact us directly.",
  },
];

export function FAQ() {
  const [openIndex, setOpenIndex] = useState<number | null>(0);

  return (
    <section id="faq" className="mx-auto max-w-3xl px-6 py-20">
      <p className="text-xs font-medium uppercase tracking-[0.18em] text-[var(--brass)]">
        FAQ
      </p>
      <h2 className="mt-3 font-[family-name:var(--font-display)] text-3xl font-semibold tracking-tight text-[var(--ink)]">
        Questions firms ask before switching
      </h2>

      <dl className="mt-10 divide-y divide-[var(--line)] border-y border-[var(--line)]">
        {FAQS.map((item, i) => {
          const open = openIndex === i;
          return (
            <div key={item.q}>
              <dt>
                <button
                  type="button"
                  onClick={() => setOpenIndex(open ? null : i)}
                  aria-expanded={open}
                  className="flex w-full items-center justify-between gap-4 py-5 text-left"
                >
                  <span className="font-[family-name:var(--font-display)] text-base font-medium text-[var(--ink)]">
                    {item.q}
                  </span>
                  <ChevronDown
                    size={18}
                    className={`shrink-0 text-[var(--ink-faint)] transition-transform duration-150 ${
                      open ? "rotate-180" : ""
                    }`}
                  />
                </button>
              </dt>
              {open && (
                <dd className="pb-5 text-sm leading-relaxed text-[var(--ink-muted)]">
                  {item.a}
                </dd>
              )}
            </div>
          );
        })}
      </dl>
    </section>
  );
}
