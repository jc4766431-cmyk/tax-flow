import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { StampSeal } from "@/components/ui/stamp-seal";

export function Hero() {
  return (
    <section className="mx-auto max-w-6xl px-6 pt-16 pb-20 sm:pt-24 sm:pb-28">
      <div className="grid grid-cols-1 items-center gap-14 lg:grid-cols-[1.05fr_0.95fr] lg:gap-10">
        <div>
          <p className="text-xs font-medium uppercase tracking-[0.18em] text-[var(--brass)]">
            Built for Indian CA &amp; tax firms
          </p>
          <h1 className="mt-4 font-[family-name:var(--font-display)] text-4xl font-semibold leading-[1.08] tracking-tight text-[var(--ink)] sm:text-5xl">
            Run tax season like a ledger,
            <br className="hidden sm:block" /> not a group chat.
          </h1>
          <p className="mt-5 max-w-lg text-base leading-relaxed text-[var(--ink-muted)] sm:text-lg">
            TaxFlow keeps every client&apos;s documents, filings, and
            deadlines in one bound record — while your clients just message
            you on WhatsApp, the way they already do.
          </p>

          <div className="mt-8 flex flex-wrap items-center gap-3">
            <Link href="/register-firm">
              <Button variant="primary" size="lg">
                Get started free
                <ArrowRight size={16} />
              </Button>
            </Link>
            <Link href="#how-it-works">
              <Button variant="outline" size="lg">
                See how filings move
              </Button>
            </Link>
          </div>

          <p className="mt-5 text-xs text-[var(--ink-faint)]">
            Free for up to 5 clients. No card required.
          </p>
        </div>

        <div className="relative mx-auto w-full max-w-sm">
          {/* The "ledger card" — a mockup tax document rendered on --paper,
              the one place this token is used, per §4. */}
          <div
            className="rounded-[var(--radius-lg)] p-6 shadow-[0_24px_60px_-24px_rgba(0,0,0,0.55)]"
            style={{ background: "var(--paper)", color: "var(--paper-ink)" }}
          >
            <div className="flex items-start justify-between border-b border-[rgba(23,35,58,0.14)] pb-4">
              <div>
                <p className="text-[10px] font-medium uppercase tracking-[0.14em] opacity-60">
                  GST Return · Q3 FY 2025–26
                </p>
                <p className="mt-1 font-[family-name:var(--font-display)] text-lg font-semibold">
                  Meridian Textiles Pvt. Ltd.
                </p>
              </div>
              <span className="tabular rounded-full bg-[var(--verified-bg)] px-2.5 py-1 text-[10px] font-medium text-[var(--verified)]">
                FILED
              </span>
            </div>

            <dl className="mt-4 space-y-2.5 text-xs">
              <div className="flex items-center justify-between">
                <dt className="opacity-60">PAN</dt>
                <dd className="tabular font-medium">AAECM1234F</dd>
              </div>
              <div className="flex items-center justify-between">
                <dt className="opacity-60">GSTIN</dt>
                <dd className="tabular font-medium">27AAECM1234F1Z5</dd>
              </div>
              <div className="flex items-center justify-between">
                <dt className="opacity-60">Filed on</dt>
                <dd className="tabular font-medium">14 Oct 2025</dd>
              </div>
              <div className="flex items-center justify-between">
                <dt className="opacity-60">Reviewed by</dt>
                <dd className="font-medium">R. Kulkarni</dd>
              </div>
            </dl>

            {/* Faint ruled lines in paper-ink, not the shared `.ledger-rule`
                utility — that one is tuned for the navy surface color, and
                would be nearly invisible against --paper. */}
            <div
              className="mt-5 h-16 rounded-[var(--radius-sm)]"
              style={{
                backgroundImage:
                  "repeating-linear-gradient(to bottom, transparent, transparent 15px, rgba(23,35,58,0.12) 15px, rgba(23,35,58,0.12) 16px)",
              }}
            />
          </div>

          <div className="absolute -bottom-6 -right-5 sm:-bottom-8 sm:-right-8">
            <StampSeal size={104} delay={0.15} />
          </div>
        </div>
      </div>
    </section>
  );
}
