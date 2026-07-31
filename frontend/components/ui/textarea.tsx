import { forwardRef, type TextareaHTMLAttributes } from "react";
import { cn } from "@/lib/utils";

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaHTMLAttributes<HTMLTextAreaElement>>(
  ({ className, ...props }, ref) => (
    <textarea
      ref={ref}
      className={cn(
        "w-full rounded-[var(--radius-sm)] border border-[var(--line-strong)] bg-[var(--bg-elevated)] px-3 py-2 text-sm text-[var(--ink)] placeholder:text-[var(--ink-faint)] outline-none transition-colors focus:border-[var(--brass)]",
        className
      )}
      {...props}
    />
  )
);
Textarea.displayName = "Textarea";
