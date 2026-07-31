import { forwardRef, type ButtonHTMLAttributes } from "react";
import { cn } from "@/lib/utils";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "ghost" | "outline";
  size?: "sm" | "md" | "lg";
}

const variantStyles: Record<string, string> = {
  primary:
    "bg-[var(--brass)] text-[#17233A] hover:bg-[var(--brass-hover)] shadow-[0_1px_0_rgba(255,255,255,0.25)_inset]",
  secondary:
    "bg-[var(--surface)] text-[var(--ink)] hover:bg-[var(--surface-hover)] border border-[var(--line-strong)]",
  ghost: "bg-transparent text-[var(--ink)] hover:bg-[var(--surface)]",
  outline:
    "bg-transparent text-[var(--ink)] border border-[var(--line-strong)] hover:border-[var(--brass)]",
};

const sizeStyles: Record<string, string> = {
  sm: "h-8 px-3 text-sm rounded-[var(--radius-sm)]",
  md: "h-10 px-4 text-sm rounded-[var(--radius-md)]",
  lg: "h-12 px-6 text-base rounded-[var(--radius-md)]",
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "primary", size = "md", ...props }, ref) => {
    return (
      <button
        ref={ref}
        className={cn(
          "inline-flex items-center justify-center gap-2 font-medium transition-colors duration-150 disabled:opacity-50 disabled:pointer-events-none",
          variantStyles[variant],
          sizeStyles[size],
          className
        )}
        {...props}
      />
    );
  }
);
Button.displayName = "Button";
