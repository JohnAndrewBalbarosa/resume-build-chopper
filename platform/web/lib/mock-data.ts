import type { UserTier } from "./permissions";

export const metrics = [
  { label: "Total Members", value: "1,248", delta: "+84 this term" },
  { label: "Active Members", value: "742", delta: "59.4% active" },
  { label: "Inactive Registrants", value: "213", delta: "1 event away" },
  { label: "Upcoming Live Events", value: "12", delta: "4 open seats" }
];

export const kanbanEvents = {
  planning: [
    { id: "evt-1", title: "AI Study Circles: CV Sprint", owner: "Computer Science Department", seats: 42 },
    { id: "evt-2", title: "TorchData Pipeline Clinic", owner: "AI Research Cluster", seats: 28 }
  ],
  approved: [
    { id: "evt-3", title: "FEU Tech Innovation Center Demo Night", owner: "External Relations", seats: 96 },
    { id: "evt-4", title: "MLOps Portfolio Review", owner: "Career Development Office", seats: 32 }
  ],
  live: [
    { id: "evt-5", title: "Deep Learning Peer Lab", owner: "Academic Affairs", seats: 64 },
    { id: "evt-6", title: "PyTorch Hack Night", owner: "Engineering Guild", seats: 120 }
  ],
  concluded: [
    { id: "evt-7", title: "NLP Reading Group: Transformers", owner: "AI Study Circles", seats: 55 },
    { id: "evt-8", title: "Computer Vision Basics Workshop", owner: "Computer Vision Guild", seats: 88 }
  ]
};

export const leaderboardRows = [
  { rank: 1, name: "Mika #7A82F", track: "Computer Vision", points: 18420, streak: 12, badges: ["CV", "Mentor"] },
  { rank: 2, name: "Jules #29C10", track: "Deep Learning", points: 17110, streak: 10, badges: ["DL", "Events"] },
  { rank: 3, name: "Ari #4D91B", track: "NLP", points: 16680, streak: 9, badges: ["NLP", "Research"] },
  { rank: 4, name: "Nia #88E2A", track: "Optimization", points: 15440, streak: 8, badges: ["Ops", "Labs"] },
  { rank: 5, name: "Ren #95F0C", track: "MLOps", points: 14180, streak: 7, badges: ["Infra", "Peer Lead"] }
];

export const skillRadar = [
  { skill: "Computer Vision", score: 86 },
  { skill: "NLP", score: 72 },
  { skill: "Optimization", score: 64 },
  { skill: "MLOps", score: 78 },
  { skill: "Data Ethics", score: 69 },
  { skill: "Research", score: 81 }
];

export const barSkills = [
  { name: "Workshops", value: 18 },
  { name: "Projects", value: 9 },
  { name: "Peer Reviews", value: 14 },
  { name: "Mentoring", value: 7 }
];

export const events = [
  {
    title: "FEU Tech Innovation Center Hackathon",
    date: "Jul 11, 2026",
    department: "Computer Science Department",
    type: "Hackathon",
    seats: 120
  },
  {
    title: "Computer Vision Lab: Campus Safety Models",
    date: "Jul 18, 2026",
    department: "AI Study Circles",
    type: "Workshop",
    seats: 48
  },
  {
    title: "NLP Paper Jam: Filipino Tech Communities",
    date: "Jul 25, 2026",
    department: "Research Cluster",
    type: "Reading Group",
    seats: 36
  },
  {
    title: "Optimization Clinic for PyTorch Training Loops",
    date: "Aug 2, 2026",
    department: "Engineering Guild",
    type: "Clinic",
    seats: 40
  }
];

export const tierSamples: UserTier[] = ["admin", "leaderboard", "active", "general"];
