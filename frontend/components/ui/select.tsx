import { forwardRef, type SelectHTMLAttributes } from "react";
import { ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";

export const Select = forwardRef<HTMLSelectElement, SelectHTMLAttributes<HTMLSelectElement>>(
  ({ className, children, ...props }, ref) => (
    <div className="relative">
      <select
        ref={ref}
        className={cn(
          "h-10 w-full appearance-none rounded-[var(--radius-sm)] border border-[var(--line-strong)] bg-[var(--bg-elevated)] px-3 pr-8 text-sm text-[var(--ink)] outline-none transition-colors focus:border-[var(--brass)]",
          className
        )}
        {...props}
      >
        {children}
      </select>
      <ChevronDown
        size={14}
        className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-[var(--ink-faint)]"
      />
    </div>
  )
);
Select.displayName = "Select";
