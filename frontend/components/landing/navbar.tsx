import Link from "next/link";
import { Button } from "@/components/ui/button";

export function Navbar() {
  return (
    <header className="sticky top-0 z-50 border-b border-[var(--line)] bg-[var(--bg)]/85 backdrop-blur">
      <nav className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
        <Link
          href="/"
          className="font-[family-name:var(--font-display)] text-xl font-semibold tracking-tight text-[var(--ink)]"
        >
          TaxFlow<span className="text-[var(--brass)]">.</span>
        </Link>
        <div className="hidden items-center gap-8 text-sm text-[var(--ink-muted)] md:flex">
          <Link href="#features" className="hover:text-[var(--ink)]">Features</Link>
          <Link href="#how-it-works" className="hover:text-[var(--ink)]">How it Works</Link>
          <Link href="#testimonials" className="hover:text-[var(--ink)]">Testimonials</Link>
          <Link href="#faq" className="hover:text-[var(--ink)]">FAQ</Link>
        </div>
        <div className="flex items-center gap-3">
          <Link href="/login">
            <Button variant="ghost" size="sm">Client Login</Button>
          </Link>
          <Link href="/register">
            <Button variant="primary" size="sm">Get Started</Button>
          </Link>
        </div>
      </nav>
    </header>
  );
}
