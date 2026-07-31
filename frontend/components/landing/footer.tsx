import Link from "next/link";

export function Footer() {
  return (
    <footer className="border-t border-[var(--line)]">
      <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-4 px-6 py-10 sm:flex-row">
        <p className="font-[family-name:var(--font-display)] text-base font-semibold tracking-tight text-[var(--ink)]">
          TaxFlow<span className="text-[var(--brass)]">.</span>
        </p>
        <div className="flex items-center gap-6 text-sm text-[var(--ink-muted)]">
          <Link href="#features" className="hover:text-[var(--ink)]">Features</Link>
          <Link href="#pricing" className="hover:text-[var(--ink)]">Pricing</Link>
          <Link href="#faq" className="hover:text-[var(--ink)]">FAQ</Link>
          <Link href="/login" className="hover:text-[var(--ink)]">Client Login</Link>
        </div>
        <p className="text-xs text-[var(--ink-faint)]">
          &copy; {new Date().getFullYear()} TaxFlow. Built for Indian CA &amp; tax firms.
        </p>
      </div>
    </footer>
  );
}
