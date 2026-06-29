"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  BarChart3,
  CalendarDays,
  Home,
  LayoutDashboard,
  Menu,
  Settings,
  Shield,
  Trophy,
  UserRound,
  X
} from "lucide-react";
import { useState } from "react";
import { cn } from "@/lib/utils";
import { ThemeToggle } from "./theme-toggle";
import { Button } from "./ui/button";
import { Badge } from "./ui/badge";

const navItems = [
  { href: "/", label: "Landing", icon: Home },
  { href: "/admin/dashboard", label: "Command Center", icon: LayoutDashboard },
  { href: "/dashboard/profile", label: "Personal Hub", icon: UserRound },
  { href: "/leaderboards", label: "Leaderboards", icon: Trophy },
  { href: "/events", label: "Events Matrix", icon: CalendarDays },
  { href: "/settings", label: "Node Settings", icon: Settings }
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);

  const sidebar = (
    <aside className="flex h-full w-72 flex-col border-r border-border bg-surface p-4">
      <div className="mb-6 flex items-center justify-between">
        <Link className="focus-ring rounded-lg" href="/">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-accent text-white">
              <BarChart3 size={20} />
            </div>
            <div>
              <p className="font-bold tracking-[-0.02em]">PyTorch FEU</p>
              <p className="text-xs text-muted">Campus Platform</p>
            </div>
          </div>
        </Link>
        <Button aria-label="Close menu" className="lg:hidden" onClick={() => setOpen(false)} size="icon" type="button" variant="ghost">
          <X size={18} />
        </Button>
      </div>
      <nav className="space-y-1">
        {navItems.map((item) => {
          const active = pathname === item.href;
          const Icon = item.icon;
          return (
            <Link
              className={cn(
                "focus-ring flex h-10 items-center gap-3 rounded-lg px-3 text-sm font-semibold transition-all duration-300 ease-in-out",
                active ? "bg-accent text-white" : "text-muted hover:bg-elevated hover:text-ink"
              )}
              href={item.href}
              key={item.href}
              onClick={() => setOpen(false)}
            >
              <Icon size={18} />
              {item.label}
            </Link>
          );
        })}
      </nav>
      <div className="mt-auto rounded-lg border border-border bg-elevated p-3">
        <div className="mb-2 flex items-center gap-2">
          <Shield className="text-accent" size={16} />
          <p className="text-sm font-semibold">RLS-first prototype</p>
        </div>
        <p className="text-xs leading-5 text-muted">Mock visibility only. Supabase policies own production access.</p>
      </div>
    </aside>
  );

  return (
    <div className="min-h-screen bg-canvas text-ink">
      <header className="sticky top-0 z-30 flex h-16 items-center justify-between border-b border-border bg-canvas/90 px-4 backdrop-blur lg:hidden">
        <Button aria-label="Open menu" onClick={() => setOpen(true)} size="icon" type="button" variant="secondary">
          <Menu size={18} />
        </Button>
        <Badge variant="orange">Prototype UI</Badge>
        <ThemeToggle />
      </header>
      <div className="hidden lg:fixed lg:inset-y-0 lg:left-0 lg:block">{sidebar}</div>
      {open && (
        <div className="fixed inset-0 z-40 lg:hidden">
          <button aria-label="Close menu backdrop" className="absolute inset-0 bg-black/60" onClick={() => setOpen(false)} type="button" />
          <div className="relative h-full">{sidebar}</div>
        </div>
      )}
      <main className="lg:pl-72">
        <div className="mx-auto w-full max-w-7xl px-4 py-6 sm:px-6 lg:px-8">{children}</div>
      </main>
    </div>
  );
}
