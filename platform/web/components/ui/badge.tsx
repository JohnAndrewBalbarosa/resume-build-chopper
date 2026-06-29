import type { HTMLAttributes } from "react";
import { cn } from "@/lib/utils";

type BadgeVariant = "default" | "orange" | "success" | "warning" | "locked";

const variants: Record<BadgeVariant, string> = {
  default: "border-border bg-elevated text-muted",
  orange: "border-accent/30 bg-accentSoft text-accent",
  success: "border-success/30 bg-success/10 text-success",
  warning: "border-warning/30 bg-warning/10 text-warning",
  locked: "border-border bg-elevated text-muted"
};

export function Badge({ className, variant = "default", ...props }: HTMLAttributes<HTMLSpanElement> & { variant?: BadgeVariant }) {
  return (
    <span
      className={cn(
        "inline-flex h-7 items-center gap-1 rounded-full border px-2.5 text-xs font-semibold",
        variants[variant],
        className
      )}
      {...props}
    />
  );
}
