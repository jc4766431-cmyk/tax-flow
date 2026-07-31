import type { LucideIcon } from "lucide-react";

export function EmptyState({
  icon: Icon,
  title,
  description,
}: {
  icon: LucideIcon;
  title: string;
  description: string;
}) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 rounded-[var(--radius-lg)] border border-dashed border-[var(--line-strong)] px-6 py-16 text-center">
      <div className="flex h-11 w-11 items-center justify-center rounded-full bg-[var(--surface-hover)] text-[var(--ink-muted)]">
        <Icon size={20} />
      </div>
      <p className="font-[family-name:var(--font-display)] text-base text-[var(--ink)]">
        {title}
      </p>
      <p className="max-w-sm text-sm text-[var(--ink-muted)]">{description}</p>
    </div>
  );
}
