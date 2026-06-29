import { Bell, KeyRound, LockKeyhole, UserCog } from "lucide-react";
import { AppShell } from "@/components/app-shell";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input, Label } from "@/components/ui/input";

const sections = [
  {
    icon: UserCog,
    title: "Account configuration",
    description: "Display name, public handle, and FEU Tech department affiliation.",
    fields: ["Display name", "Public handle", "Department"]
  },
  {
    icon: KeyRound,
    title: "Credential management",
    description: "School email, connected identity providers, and device sessions.",
    fields: ["School email", "Backup email", "Session label"]
  },
  {
    icon: Bell,
    title: "Notification preferences",
    description: "Event access alerts, leaderboard movement, and AI recommendation summaries.",
    fields: ["Event alerts", "Leaderboard digest", "Recommendation digest"]
  },
  {
    icon: LockKeyhole,
    title: "Privacy parameters",
    description: "Public profile fields, social parsing consent, and aggregate analytics sharing.",
    fields: ["Public profile", "Social parsing consent", "Analytics sharing"]
  }
];

export default function SettingsPage() {
  return (
    <AppShell>
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-3xl font-bold tracking-[-0.02em]">Node System Settings</h1>
          <p className="mt-2 text-muted">Account, credential, notification, and privacy controls for the campus node.</p>
        </div>
        <Badge variant="orange">Privacy by default</Badge>
      </div>

      <section className="grid gap-4 lg:grid-cols-2">
        {sections.map((section) => {
          const Icon = section.icon;
          return (
            <Card className="bg-surface" key={section.title}>
              <CardHeader>
                <div>
                  <CardTitle>{section.title}</CardTitle>
                  <CardDescription>{section.description}</CardDescription>
                </div>
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-accentSoft text-accent">
                  <Icon size={20} />
                </div>
              </CardHeader>
              <div className="grid gap-3">
                {section.fields.map((field) => (
                  <div key={field}>
                    <Label htmlFor={field.toLowerCase().replaceAll(" ", "-")}>{field}</Label>
                    <Input id={field.toLowerCase().replaceAll(" ", "-")} placeholder={`Configure ${field.toLowerCase()}`} />
                  </div>
                ))}
              </div>
              <div className="mt-5 flex justify-end">
                <Button type="button">Save section</Button>
              </div>
            </Card>
          );
        })}
      </section>
    </AppShell>
  );
}
