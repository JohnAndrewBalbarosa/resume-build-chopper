"use client";

import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  PolarAngleAxis,
  PolarGrid,
  Radar,
  RadarChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from "recharts";
import { activityTrend, barSkills, departmentLoad, skillRadar } from "@/lib/mock-data";

const tooltipStyle = {
  background: "var(--surface)",
  border: "1px solid var(--border)",
  borderRadius: 8,
  color: "var(--ink)"
};

export function SkillRadarChart() {
  return (
    <div className="h-72 w-full">
      <ResponsiveContainer>
        <RadarChart data={skillRadar}>
          <PolarGrid stroke="rgba(122,139,158,0.35)" />
          <PolarAngleAxis dataKey="skill" tick={{ fill: "var(--muted)", fontSize: 12 }} />
          <Radar dataKey="score" fill="var(--accent)" fillOpacity={0.28} stroke="var(--accent)" strokeWidth={2} />
          <Tooltip contentStyle={tooltipStyle} />
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
          <Tooltip contentStyle={tooltipStyle} />
          <Bar dataKey="value" fill="var(--accent)" radius={[6, 6, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export function ActivityTrendChart() {
  return (
    <div className="h-72 w-full">
      <ResponsiveContainer>
        <AreaChart data={activityTrend}>
          <defs>
            <linearGradient id="activity-orange" x1="0" x2="0" y1="0" y2="1">
              <stop offset="5%" stopColor="var(--accent)" stopOpacity={0.42} />
              <stop offset="95%" stopColor="var(--accent)" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid stroke="rgba(255,255,255,0.06)" vertical={false} />
          <XAxis dataKey="day" tick={{ fill: "var(--muted)", fontSize: 12 }} tickLine={false} />
          <YAxis tick={{ fill: "var(--muted)", fontSize: 12 }} tickLine={false} />
          <Tooltip contentStyle={tooltipStyle} />
          <Area dataKey="contributions" fill="url(#activity-orange)" stroke="var(--accent)" strokeWidth={2} type="monotone" />
          <Line dataKey="events" dot={false} stroke="var(--info)" strokeWidth={2} type="monotone" />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

export function DepartmentLoadChart() {
  return (
    <div className="h-64 w-full">
      <ResponsiveContainer>
        <BarChart data={departmentLoad} layout="vertical" margin={{ left: 16 }}>
          <CartesianGrid horizontal={false} stroke="rgba(255,255,255,0.06)" />
          <XAxis tick={{ fill: "var(--muted)", fontSize: 12 }} type="number" />
          <YAxis dataKey="department" tick={{ fill: "var(--muted)", fontSize: 12 }} tickLine={false} type="category" width={86} />
          <Tooltip contentStyle={tooltipStyle} />
          <Bar dataKey="open" fill="var(--accent)" radius={[0, 6, 6, 0]} />
          <Bar dataKey="approved" fill="rgba(255,255,255,0.22)" radius={[0, 6, 6, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
