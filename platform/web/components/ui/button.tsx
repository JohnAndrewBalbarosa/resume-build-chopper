import type { ButtonHTMLAttributes } from "react";
import { cn } from "@/lib/utils";

type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: ButtonVariant;
  size?: "sm" | "md" | "lg" | "icon";
};

const variants: Record<ButtonVariant, string> = {
  primary: "bg-accent text-white hover:bg-accent/90 active:bg-accent/80",
  secondary: "border border-border bg-elevated text-ink hover:bg-surface",
  ghost: "text-muted hover:bg-elevated hover:text-ink",
  danger: "bg-danger text-white hover:bg-danger/90"
};

const sizes = {
  sm: "h-8 px-3 text-sm",
  md: "h-10 px-4 text-sm",
  lg: "h-11 px-5 text-base",
  icon: "h-10 w-10 p-0"
};

export function Button({ className, variant = "primary", size = "md", ...props }: ButtonProps) {
  return (
    <button
      className={cn(
        "focus-ring inline-flex items-center justify-center gap-2 rounded-full font-semibold transition-all duration-300 ease-in-out disabled:pointer-events-none disabled:opacity-50",
        variants[variant],
        sizes[size],
        className
      )}
      {...props}
    />
  );
}
