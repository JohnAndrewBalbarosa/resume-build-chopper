import Link from "next/link";
import { ArrowRight, Building2, Flame, ShieldCheck, Trophy } from "lucide-react";
import { leaderboardRows } from "@/lib/mock-data";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { ParticleField } from "@/components/particle-field";

const nav = ["Partners", "About", "Perks", "Leaderboards"];

export default function LandingPage() {
  return (
    <main className="min-h-screen bg-canvas text-ink">
      <header className="fixed inset-x-0 top-0 z-40 border-b border-white/10 bg-[#0B0B0C]/88 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
          <Link className="focus-ring rounded-lg text-sm font-bold text-white" href="/">
            PyTorch FEU Tech
          </Link>
          <nav className="hidden items-center gap-6 md:flex">
            {nav.map((item) => (
              <a className="focus-ring rounded-lg text-sm font-semibold text-[#7A8B9E] hover:text-white" href={`#${item.toLowerCase()}`} key={item}>
                {item}
              </a>
            ))}
          </nav>
          <Link
            className="focus-ring inline-flex h-9 items-center justify-center rounded-full bg-accent px-4 text-sm font-semibold text-white transition-all duration-300 ease-in-out hover:bg-accent/90"
            href="/auth"
          >
            Login
          </Link>
        </div>
      </header>

      <section className="relative min-h-[92vh] overflow-hidden bg-[#0B0B0C] pt-16 text-white">
        <ParticleField density={96} />
        <div className="relative z-10 mx-auto flex min-h-[calc(92vh-4rem)] max-w-7xl items-center px-4 py-20 sm:px-6 lg:px-8">
          <div className="max-w-3xl">
            <Badge variant="orange">Community Intelligence Hub</Badge>
            <h1 className="mt-6 max-w-2xl text-5xl font-extrabold tracking-[-0.02em] sm:text-6xl">
              PyTorch FEU Tech Campus Platform
            </h1>
            <p className="mt-6 max-w-2xl text-lg leading-8 text-[#B6C2D1]">
              A normalized member-growth system for campus events, skills, merit, leaderboards, and public-safe career intelligence.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Link
                className="focus-ring inline-flex h-11 items-center justify-center gap-2 rounded-full bg-accent px-5 font-semibold text-white transition-all duration-300 ease-in-out hover:bg-accent/90"
                href="/dashboard/profile"
              >
                Open Personal Hub <ArrowRight size={18} />
              </Link>
              <Link
                className="focus-ring inline-flex h-11 items-center justify-center rounded-full border border-white/15 bg-white/10 px-5 font-semibold text-white transition-all duration-300 ease-in-out hover:bg-white/15"
                href="/admin/dashboard"
              >
                View Command Center
              </Link>
            </div>
          </div>
        </div>
      </section>

      <section className="mx-auto grid max-w-7xl gap-12 px-4 py-16 sm:px-6 lg:px-8">
        <div className="grid gap-6 lg:grid-cols-2" id="partners">
          <div>
            <h2 className="text-3xl font-bold tracking-[-0.02em]">Ecosystem partners row</h2>
            <p className="mt-4 max-w-2xl leading-7 text-muted">
              Designed around FEU Tech Innovation Center, Computer Science Department, AI Study Circles, and chapter partner workflows.
            </p>
          </div>
          <Card className="grid grid-cols-2 gap-3 bg-elevated sm:grid-cols-4">
            {["FEU Tech Hub", "PyTorch Portal", "AI Study Circles", "CS Department"].map((partner) => (
              <div className="rounded-lg border border-border bg-surface p-3 text-sm font-semibold" key={partner}>
                {partner}
              </div>
            ))}
          </Card>
        </div>

        <div className="grid gap-6 lg:grid-cols-[0.9fr_1.1fr]" id="about">
          <Card className="under-glow bg-surface">
            <Building2 className="mb-4 text-accent" size={24} />
            <h2 className="text-2xl font-bold tracking-[-0.02em]">About PyTorch Campus Mission</h2>
            <p className="mt-4 leading-7 text-muted">
              Members build evidence through events, projects, peer reviews, and curated social signals. Outputs stay disposable; normalized records stay canonical.
            </p>
          </Card>
          <div className="grid gap-4 sm:grid-cols-2" id="perks">
            {[
              ["Early access", "Active members see workshop notifications before general release."],
              ["Merit blocks", "Awards reflect verified participation and chapter-approved achievements."],
              ["Public-safe rank", "Leaderboards expose handles and scores, never private raw records."],
              ["AI drafts", "Recommendations assist officers while human review remains required."]
            ].map(([title, copy]) => (
              <Card key={title}>
                <Flame className="mb-3 text-accent" size={20} />
                <h3 className="font-bold">{title}</h3>
                <p className="mt-2 text-sm leading-6 text-muted">{copy}</p>
              </Card>
            ))}
          </div>
        </div>

        <Card className="bg-elevated" id="leaderboards">
          <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="text-2xl font-bold tracking-[-0.02em]">Top 3 Active Member Ticker</h2>
              <p className="mt-1 text-sm text-muted">Campus rank uses event streaks and reviewed activity scores.</p>
            </div>
            <Badge variant="orange">
              <Trophy size={14} />
              Live mock
            </Badge>
          </div>
          <div className="grid gap-3 md:grid-cols-3">
            {leaderboardRows.slice(0, 3).map((row) => (
              <div className="rounded-lg border border-border bg-surface p-4" key={row.name}>
                <div className="flex items-center justify-between">
                  <span className="data-label text-accent">#{row.rank}</span>
                  <ShieldCheck className="text-success" size={18} />
                </div>
                <p className="mt-4 font-bold">{row.name}</p>
                <p className="text-sm text-muted">{row.track}</p>
                <p className="data-label mt-3 text-sm">{row.points.toLocaleString()} pts</p>
              </div>
            ))}
          </div>
        </Card>
      </section>

      <footer className="sticky bottom-0 border-t border-border bg-surface/95 px-4 py-3 text-sm backdrop-blur">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-3">
          <div className="flex gap-4 text-muted">
            <a className="focus-ring rounded-lg hover:text-ink" href="https://pytorch.org">Official PyTorch Portal</a>
            <a className="focus-ring rounded-lg hover:text-ink" href="https://www.feutech.edu.ph">Official FEU Tech Hub</a>
          </div>
          <p className="text-muted">Copyright PyTorch FEU Tech Campus 2026. All rights reserved.</p>
        </div>
      </footer>
    </main>
  );
}
