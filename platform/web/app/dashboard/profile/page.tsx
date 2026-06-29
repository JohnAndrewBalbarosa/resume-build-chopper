"use client";

import { Facebook, Linkedin, Medal, Plug, UserRound } from "lucide-react";
import { useState } from "react";
import { AppShell } from "@/components/app-shell";
import { SkillBarChart, SkillRadarChart } from "@/components/charts";
import { GatePanel } from "@/components/role-gate";
import { Badge } from "@/components/ui/badge";
import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { SegmentedTabs } from "@/components/ui/tabs";
import { userTiers, type UserTier } from "@/lib/permissions";

const tierTabs = [
  { value: "active", label: "Active" },
  { value: "leaderboard", label: "Elite" },
  { value: "general", label: "General" }
] satisfies Array<{ value: UserTier; label: string }>;

export default function ProfilePage() {
  const [tier, setTier] = useState<UserTier>("active");

  return (
    <AppShell>
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-3xl font-bold tracking-[-0.02em]">User Profile & Personal Hub</h1>
          <p className="mt-2 text-muted">Student growth profile with consent-based social connectors and skill telemetry.</p>
        </div>
        <SegmentedTabs items={tierTabs} onChange={setTier} value={tier} />
      </div>

      <div className="grid gap-4 lg:grid-cols-[1fr_0.75fr]">
        <Card className="bg-surface">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div className="flex items-center gap-4">
              <div className="flex h-16 w-16 items-center justify-center rounded-lg bg-accent text-white">
                <UserRound size={30} />
              </div>
              <div>
                <h2 className="text-xl font-bold tracking-[-0.02em]">Mika Santos #7A82F</h2>
                <p className="text-sm text-muted">BS Computer Science, FEU Tech Innovation Center cohort</p>
                <div className="mt-3 flex flex-wrap gap-2">
                  <Badge variant="orange">Computer Vision</Badge>
                  <Badge variant="success">AI Study Circles</Badge>
                  <Badge>2026 member</Badge>
                </div>
              </div>
            </div>
            <Badge variant="orange">{userTiers[tier].label}</Badge>
          </div>
        </Card>

        <Card className="bg-elevated">
          <CardHeader>
            <div>
              <CardTitle>Social connectors</CardTitle>
              <CardDescription>Client-side parsing only; raw text stays private until reviewed.</CardDescription>
            </div>
            <Plug className="text-accent" size={20} />
          </CardHeader>
          <div className="grid gap-3 sm:grid-cols-2">
            <button className="focus-ring flex items-center justify-between rounded-lg border border-border bg-surface p-3 text-left transition-all duration-300 ease-in-out hover:bg-elevated" type="button">
              <span className="flex items-center gap-2 font-semibold"><Linkedin size={18} /> LinkedIn</span>
              <Badge variant="success">Linked</Badge>
            </button>
            <button className="focus-ring flex items-center justify-between rounded-lg border border-border bg-surface p-3 text-left transition-all duration-300 ease-in-out hover:bg-elevated" type="button">
              <span className="flex items-center gap-2 font-semibold"><Facebook size={18} /> Facebook</span>
              <Badge>Ready</Badge>
            </button>
          </div>
        </Card>
      </div>

      <div className="mt-4">
        <GatePanel tier={tier} />
      </div>

      <section className="mt-4 grid gap-4 lg:grid-cols-[1.05fr_0.95fr]">
        <Card className="bg-surface">
          <CardHeader>
            <div>
              <CardTitle>UpSkill radar</CardTitle>
              <CardDescription>Sub-field profile generated from verified campus activity.</CardDescription>
            </div>
            <Medal className="text-accent" size={20} />
          </CardHeader>
          <SkillRadarChart />
        </Card>
        <Card className="bg-surface">
          <CardHeader>
            <div>
              <CardTitle>Merit activity blocks</CardTitle>
              <CardDescription>Evidence categories behind personal recommendations.</CardDescription>
            </div>
          </CardHeader>
          <SkillBarChart />
        </Card>
      </section>
    </AppShell>
  );
}
