import {
  Activity,
  AlertTriangle,
  ArrowUpRight,
  CalendarCheck,
  CheckCircle2,
  Clock3,
  LockKeyhole,
  ShieldCheck,
  Sparkles,
  Trophy,
  Users,
  Zap
} from "lucide-react";
import { AppShell } from "@/components/app-shell";
import { ActivityTrendChart, DepartmentLoadChart, SkillRadarChart } from "@/components/charts";
import { KanbanBoard } from "@/components/kanban-board";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { approvalQueue, leaderboardRows, metrics, systemHealth } from "@/lib/mock-data";
import { cn, formatRank } from "@/lib/utils";

const metricIcons = [Users, Activity, AlertTriangle, CalendarCheck];

function MetricRibbon() {
  return (
    <section className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
      {metrics.map((metric, index) => {
        const Icon = metricIcons[index];
        const positive = metric.trend === "up";
        return (
          <Card className="border-white/10 bg-[#141416] p-4 hover:border-[#e8590c]/35" key={metric.label}>
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-sm text-[#FFF7ED]/48">{metric.label}</p>
                <p className="data-label mt-3 text-3xl font-bold text-[#FFF7ED]">{metric.value}</p>
                <p className={cn("mt-2 text-xs", positive ? "text-green-400" : "text-[#fb7185]")}>{metric.delta} this cycle</p>
              </div>
              <div className="flex h-10 w-10 items-center justify-center rounded-lg border border-[#e8590c]/25 bg-[#e8590c]/10 text-[#e8590c]">
                <Icon size={20} />
              </div>
            </div>
          </Card>
        );
      })}
    </section>
  );
}

function HealthRail() {
  return (
    <Card className="border-white/10 bg-[#141416]">
      <div className="mb-4 flex items-center justify-between gap-3">
        <div>
          <h2 className="font-bold tracking-[-0.02em] text-[#FFF7ED]">Trust boundary</h2>
          <p className="mt-1 text-sm text-[#FFF7ED]/50">Prototype safety signals officers should see before dispatch.</p>
        </div>
        <ShieldCheck className="text-[#e8590c]" size={20} />
      </div>
      <div className="grid gap-3 sm:grid-cols-2">
        {systemHealth.map((item) => (
          <div className="rounded-lg border border-white/10 bg-[#0d0d0d] p-3" key={item.label}>
            <div className="mb-3 flex items-center justify-between">
              <p className="text-xs text-[#FFF7ED]/45">{item.label}</p>
              <span
                className={cn(
                  "h-2 w-2 rounded-full",
                  item.tone === "good" && "bg-green-400",
                  item.tone === "warn" && "bg-yellow-300",
                  item.tone === "info" && "bg-blue-400"
                )}
              />
            </div>
            <p className="data-label text-2xl font-bold text-[#FFF7ED]">{item.value}</p>
          </div>
        ))}
      </div>
    </Card>
  );
}

function ApprovalQueue() {
  return (
    <Card className="border-white/10 bg-[#141416]">
      <div className="mb-4 flex items-center justify-between gap-3">
        <div>
          <h2 className="font-bold tracking-[-0.02em] text-[#FFF7ED]">Approval middleman</h2>
          <p className="mt-1 text-sm text-[#FFF7ED]/50">AI output waits for department review.</p>
        </div>
        <Badge variant="orange">HITL</Badge>
      </div>
      <div className="space-y-3">
        {approvalQueue.map((item) => (
          <article className="rounded-lg border border-white/10 bg-[#0d0d0d] p-3" key={item.title}>
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="font-semibold leading-5 text-[#FFF7ED]">{item.title}</p>
                <p className="mt-2 text-xs text-[#FFF7ED]/45">{item.department}</p>
              </div>
              <Badge variant={item.risk === "public" ? "warning" : "default"}>{item.risk}</Badge>
            </div>
            <div className="mt-3 flex items-center justify-between gap-3 text-xs text-[#FFF7ED]/45">
              <span className="flex items-center gap-1.5"><Clock3 size={13} />{item.age}</span>
              <span>{item.status}</span>
            </div>
          </article>
        ))}
      </div>
    </Card>
  );
}

function LeaderboardPanel() {
  return (
    <Card className="border-white/10 bg-[#141416]">
      <div className="mb-4 flex items-center justify-between gap-3">
        <div>
          <h2 className="font-bold tracking-[-0.02em] text-[#FFF7ED]">Elite node rank</h2>
          <p className="mt-1 text-sm text-[#FFF7ED]/50">Public-safe handles only.</p>
        </div>
        <Trophy className="text-[#e8590c]" size={20} />
      </div>
      <div className="space-y-2">
        {leaderboardRows.slice(0, 5).map((row) => (
          <div className="flex items-center justify-between rounded-lg border border-white/10 bg-[#0d0d0d] p-3" key={row.name}>
            <div className="flex min-w-0 items-center gap-3">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg border border-[#e8590c]/30 bg-[#e8590c]/10 font-mono text-xs text-[#e8590c]">
                {formatRank(row.rank)}
              </div>
              <div className="min-w-0">
                <p className="truncate text-sm font-semibold text-[#FFF7ED]">{row.name}</p>
                <p className="truncate text-xs text-[#FFF7ED]/45">{row.track}</p>
              </div>
            </div>
            <p className="data-label text-sm text-[#e8590c]">{row.points.toLocaleString()}</p>
          </div>
        ))}
      </div>
    </Card>
  );
}

function OperationsHero() {
  return (
    <section className="relative overflow-hidden rounded-2xl border border-white/10 bg-[#141416] p-5 lg:p-6">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_16%_0%,rgba(232,89,12,0.22),transparent_32%)]" />
      <div className="relative flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <div className="mb-4 flex flex-wrap items-center gap-2">
            <Badge variant="orange"><Sparkles size={14} /> Officer command</Badge>
            <Badge>Cycle 2026-Q3</Badge>
            <Badge variant="success"><CheckCircle2 size={14} /> RLS mock-safe</Badge>
          </div>
          <h1 className="max-w-3xl text-3xl font-extrabold tracking-[-0.02em] text-[#FFF7ED] md:text-4xl">
            Campus intelligence dashboard for chapter operations.
          </h1>
          <p className="mt-3 max-w-2xl leading-7 text-[#FFF7ED]/58">
            One surface for member telemetry, event throughput, leaderboard pressure, approval bottlenecks, and AI-assisted briefs.
          </p>
        </div>
        <div className="grid min-w-[280px] grid-cols-2 gap-3">
          <div className="rounded-lg border border-white/10 bg-[#0d0d0d] p-3">
            <p className="text-xs text-[#FFF7ED]/45">Pipeline status</p>
            <p className="data-label mt-2 text-xl font-bold text-green-400">LIVE</p>
          </div>
          <div className="rounded-lg border border-white/10 bg-[#0d0d0d] p-3">
            <p className="text-xs text-[#FFF7ED]/45">Risk flags</p>
            <p className="data-label mt-2 text-xl font-bold text-[#e8590c]">03</p>
          </div>
        </div>
      </div>
    </section>
  );
}

export function DashboardCommandCenter() {
  return (
    <AppShell>
      <div className="space-y-4">
        <OperationsHero />
        <MetricRibbon />

        <section className="grid gap-4 xl:grid-cols-[1.35fr_0.65fr]">
          <Card className="border-white/10 bg-[#141416]">
            <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
              <div>
                <h2 className="font-bold tracking-[-0.02em] text-[#FFF7ED]">Weekly activity pulse</h2>
                <p className="mt-1 text-sm text-[#FFF7ED]/50">Events and member contributions tracked by day.</p>
              </div>
              <Badge variant="orange"><Zap size={14} /> +18% engagement</Badge>
            </div>
            <ActivityTrendChart />
          </Card>

          <HealthRail />
        </section>

        <section className="grid gap-4 xl:grid-cols-[0.82fr_1.18fr]">
          <Card className="border-white/10 bg-[#141416]">
            <div className="mb-4 flex items-center justify-between gap-3">
              <div>
                <h2 className="font-bold tracking-[-0.02em] text-[#FFF7ED]">Department load</h2>
                <p className="mt-1 text-sm text-[#FFF7ED]/50">Open work versus approved capacity.</p>
              </div>
              <ArrowUpRight className="text-[#e8590c]" size={20} />
            </div>
            <DepartmentLoadChart />
          </Card>

          <Card className="border-white/10 bg-[#141416]">
            <KanbanBoard />
          </Card>
        </section>

        <section className="grid gap-4 xl:grid-cols-3">
          <ApprovalQueue />
          <LeaderboardPanel />
          <Card className="border-white/10 bg-[#141416]">
            <div className="mb-4 flex items-center justify-between gap-3">
              <div>
                <h2 className="font-bold tracking-[-0.02em] text-[#FFF7ED]">Chapter skill radar</h2>
                <p className="mt-1 text-sm text-[#FFF7ED]/50">Aggregated, anonymous readiness mix.</p>
              </div>
              <LockKeyhole className="text-[#e8590c]" size={20} />
            </div>
            <SkillRadarChart />
          </Card>
        </section>
      </div>
    </AppShell>
  );
}
