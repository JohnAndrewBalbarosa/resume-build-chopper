"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  BarChart3,
  CalendarDays,
  Flame,
  Home,
  LayoutDashboard,
  Menu,
  Search,
  Settings,
  Shield,
  Trophy,
  UserRound,
  X
} from "lucide-react";
import { useState } from "react";
import { cn } from "@/lib/utils";
import { Button } from "./ui/button";
import { Badge } from "./ui/badge";

const navItems = [
  { href: "/", label: "Landing", icon: Home },
  { href: "/dashboard", label: "Command Center", icon: LayoutDashboard },
  { href: "/dashboard/profile", label: "Personal Hub", icon: UserRound },
  { href: "/leaderboards", label: "Leaderboards", icon: Trophy },
  { href: "/events", label: "Events Matrix", icon: CalendarDays },
  { href: "/settings", label: "Node Settings", icon: Settings }
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);

  const sidebar = (
    <aside className="flex h-full w-72 flex-col border-r border-white/10 bg-[#0d0d0d] p-4 text-[#FFF7ED]">
      <div className="mb-6 flex items-center justify-between">
        <Link className="focus-ring rounded-lg" href="/">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-gradient-to-br from-[#e8590c] to-[#ff8a3d] shadow-lg shadow-[#e8590c]/30">
              <Flame size={20} />
            </div>
            <div>
              <p className="font-mono text-sm font-bold tracking-[-0.02em]">PYTORCH.FIT</p>
              <p className="text-xs text-[#FFF7ED]/45">Campus Engine</p>
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
                active ? "bg-[#e8590c] text-white" : "text-[#FFF7ED]/55 hover:bg-white/[0.06] hover:text-[#FFF7ED]"
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
      <div className="mt-6 rounded-lg border border-white/10 bg-white/[0.035] p-3">
        <div className="mb-2 flex items-center justify-between gap-2">
          <p className="font-mono text-[10px] uppercase tracking-widest text-[#FFF7ED]/40">Current cycle</p>
          <span className="h-1.5 w-1.5 rounded-full bg-green-400" />
        </div>
        <div className="h-1.5 overflow-hidden rounded-full bg-white/10">
          <div className="h-full w-[68%] rounded-full bg-[#e8590c]" />
        </div>
        <p className="mt-2 text-xs text-[#FFF7ED]/45">68% event readiness across officer pipeline.</p>
      </div>
      <div className="mt-auto rounded-lg border border-white/10 bg-white/[0.035] p-3">
        <div className="mb-2 flex items-center gap-2">
          <Shield className="text-[#e8590c]" size={16} />
          <p className="text-sm font-semibold">RLS-first prototype</p>
        </div>
        <p className="text-xs leading-5 text-[#FFF7ED]/45">Mock visibility only. Supabase policies own production access.</p>
      </div>
    </aside>
  );

  return (
    <div className="min-h-screen bg-[#0b0b0c] text-[#FFF7ED]">
      <header className="sticky top-0 z-30 flex h-16 items-center justify-between border-b border-white/10 bg-[#0b0b0c]/90 px-4 backdrop-blur lg:hidden">
        <Button aria-label="Open menu" onClick={() => setOpen(true)} size="icon" type="button" variant="secondary">
          <Menu size={18} />
        </Button>
        <Badge variant="orange">Prototype UI</Badge>
        <Button aria-label="Search" size="icon" type="button" variant="secondary">
          <Search size={18} />
        </Button>
      </header>
      <div className="hidden lg:fixed lg:inset-y-0 lg:left-0 lg:block">{sidebar}</div>
      {open && (
        <div className="fixed inset-0 z-40 lg:hidden">
          <button aria-label="Close menu backdrop" className="absolute inset-0 bg-black/60" onClick={() => setOpen(false)} type="button" />
          <div className="relative h-full">{sidebar}</div>
        </div>
      )}
      <main className="lg:pl-72">
        <div className="mx-auto w-full max-w-[1500px] px-4 py-6 sm:px-6 lg:px-8">{children}</div>
      </main>
    </div>
  );
}
