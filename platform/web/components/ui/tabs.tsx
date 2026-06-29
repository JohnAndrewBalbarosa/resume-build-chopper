"use client";

import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

export function SegmentedTabs<T extends string>({
  items,
  value,
  onChange
}: {
  items: Array<{ value: T; label: string }>;
  value: T;
  onChange: (value: T) => void;
}) {
  return (
    <div className="inline-flex max-w-full gap-1 rounded-full border border-border bg-elevated p-1">
      {items.map((item) => (
        <button
          key={item.value}
          onClick={() => onChange(item.value)}
          className={cn(
            "focus-ring h-8 rounded-full px-3 text-sm font-semibold transition-all duration-300 ease-in-out",
            value === item.value ? "bg-accent text-white" : "text-muted hover:text-ink"
          )}
          type="button"
        >
          {item.label}
        </button>
      ))}
    </div>
  );
}

export function TabPanel({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={cn("mt-4", className)}>{children}</div>;
}
