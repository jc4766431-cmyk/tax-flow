import Link from "next/link";

export function AuthCard({
  title,
  subtitle,
  children,
  footer,
}: {
  title: string;
  subtitle: string;
  children: React.ReactNode;
  footer: React.ReactNode;
}) {
  return (
    <div className="w-full max-w-[420px]">
      <Link
        href="/"
        className="mb-8 block text-center font-[family-name:var(--font-display)] text-2xl font-semibold tracking-tight text-[var(--ink)]"
      >
        TaxFlow<span className="text-[var(--brass)]">.</span>
      </Link>
      <div className="rounded-[var(--radius-lg)] border border-[var(--line-strong)] bg-[var(--surface)] p-8 shadow-[0_1px_0_rgba(237,234,224,0.05)_inset]">
        <h1 className="font-[family-name:var(--font-display)] text-xl font-semibold text-[var(--ink)]">
          {title}
        </h1>
        <p className="mt-1 text-sm text-[var(--ink-muted)]">{subtitle}</p>
        <div className="mt-6">{children}</div>
      </div>
      <p className="mt-6 text-center text-sm text-[var(--ink-muted)]">{footer}</p>
    </div>
  );
}
