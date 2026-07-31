import { cn } from "@/lib/utils";

type BadgeTone = "neutral" | "verified" | "overdue" | "pending" | "brass";

const toneStyles: Record<BadgeTone, string> = {
  neutral: "bg-[var(--surface-hover)] text-[var(--ink-muted)]",
  verified: "bg-[var(--verified-bg)] text-[var(--verified)]",
  overdue: "bg-[var(--overdue-bg)] text-[var(--overdue)]",
  pending: "bg-[var(--pending-bg)] text-[var(--pending)]",
  brass: "bg-[var(--brass)]/15 text-[var(--brass)]",
};

export function Badge({
  tone = "neutral",
  className,
  ...props
}: React.HTMLAttributes<HTMLSpanElement> & { tone?: BadgeTone }) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium tracking-wide",
        toneStyles[tone],
        className
      )}
      {...props}
    />
  );
}
