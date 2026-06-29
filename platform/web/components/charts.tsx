"use client";

import {
  Bar,
  BarChart,
  PolarAngleAxis,
  PolarGrid,
  Radar,
  RadarChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from "recharts";
import { barSkills, skillRadar } from "@/lib/mock-data";

export function SkillRadarChart() {
  return (
    <div className="h-72 w-full">
      <ResponsiveContainer>
        <RadarChart data={skillRadar}>
          <PolarGrid stroke="rgba(122,139,158,0.35)" />
          <PolarAngleAxis dataKey="skill" tick={{ fill: "var(--muted)", fontSize: 12 }} />
          <Radar dataKey="score" fill="var(--accent)" fillOpacity={0.28} stroke="var(--accent)" strokeWidth={2} />
          <Tooltip contentStyle={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 8 }} />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
}

export function SkillBarChart() {
  return (
    <div className="h-64 w-full">
      <ResponsiveContainer>
        <BarChart data={barSkills}>
          <XAxis dataKey="name" tick={{ fill: "var(--muted)", fontSize: 12 }} />
          <YAxis tick={{ fill: "var(--muted)", fontSize: 12 }} />
          <Tooltip contentStyle={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 8 }} />
          <Bar dataKey="value" fill="var(--accent)" radius={[6, 6, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
