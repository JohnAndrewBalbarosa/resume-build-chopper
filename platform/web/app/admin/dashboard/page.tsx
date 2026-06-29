import { Activity, AlertTriangle, CalendarCheck, Users } from "lucide-react";
import { AppShell } from "@/components/app-shell";
import { KanbanBoard } from "@/components/kanban-board";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { metrics } from "@/lib/mock-data";

const icons = [Users, Activity, AlertTriangle, CalendarCheck];

export default function AdminDashboardPage() {
  return (
    <AppShell>
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-3xl font-bold tracking-[-0.02em]">Administrative Command Center</h1>
          <p className="mt-2 text-muted">Executive visibility for member analytics, event flow, and approval-ready operations.</p>
        </div>
        <Badge variant="orange">Execs & Officers</Badge>
      </div>

      <section className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        {metrics.map((metric, index) => {
          const Icon = icons[index];
          return (
            <Card className="bg-surface" key={metric.label}>
              <div className="flex items-center justify-between gap-4">
                <div>
                  <p className="text-sm text-muted">{metric.label}</p>
                  <p className="data-label mt-3 text-3xl font-bold">{metric.value}</p>
                  <p className="mt-2 text-xs text-muted">{metric.delta}</p>
                </div>
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-accentSoft text-accent">
                  <Icon size={20} />
                </div>
              </div>
            </Card>
          );
        })}
      </section>

      <Card className="mt-6 bg-surface">
        <KanbanBoard />
      </Card>
    </AppShell>
  );
}
