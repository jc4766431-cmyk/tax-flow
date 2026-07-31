import type { LucideIcon } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

/**
 * Small stat/metric card used on both dashboard overview screens (§3d
 * client portal, §3e accountant dashboard). Numbers always render in the
 * mono `.tabular` face per HANDOFF.md §4's design direction — anything
 * that's a figure gets the ledger treatment, not the display serif.
 */
export function StatCard({
  label,
  value,
  icon: Icon,
  tone = "neutral",
}: {
  label: string;
  value: number | string;
  icon: LucideIcon;
  tone?: "neutral" | "overdue" | "brass";
}) {
  const iconToneStyles: Record<string, string> = {
    neutral: "bg-[var(--surface-hover)] text-[var(--ink-muted)]",
    overdue: "bg-[var(--overdue-bg)] text-[var(--overdue)]",
    brass: "bg-[var(--brass)]/15 text-[var(--brass)]",
  };

  return (
    <Card>
      <CardContent className="flex items-start justify-between gap-3 p-5">
        <div className="min-w-0">
          <p className="text-xs font-medium uppercase tracking-wide text-[var(--ink-muted)]">
            {label}
          </p>
          <p className="tabular mt-2 text-3xl font-semibold text-[var(--ink)]">
            {value}
          </p>
        </div>
        <div
          className={cn(
            "flex h-9 w-9 shrink-0 items-center justify-center rounded-[var(--radius-sm)]",
            iconToneStyles[tone]
          )}
        >
          <Icon size={18} />
        </div>
      </CardContent>
    </Card>
  );
}
