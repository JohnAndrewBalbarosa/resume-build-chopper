# Design

## System
PyTorch FEU Tech Campus Platform uses a restrained product UI with an obsidian-first dark mode, soft off-white light mode, and PyTorch orange as the only primary accent. Typography uses Plus Jakarta Sans with system fallbacks.

## Color Tokens
- Canvas dark: `#0B0B0C`
- Surface dark: `#141416`
- Text dark: `#FFFFFF`
- Muted dark: `#7A8B9E`
- Canvas light: `#FAFAFA`
- Surface light: `#FFFFFF`
- Text light: `#0F172A`
- Muted light: `#64748B`
- Primary accent: `#E8590C`
- Warm accent tint: `#FFF7ED`

## Layout
Authenticated routes use a persistent sidebar shell with compact mobile drawer. Dashboards use bento grids, dense ribbons, tables, and charts. Public and auth routes use full-viewport canvas treatments backed by particle motion.

## Components
Cards use 8px radius, 1px boundaries, and restrained hover lift. Buttons use consistent sizes, Lucide icons, and strong focus states. Tables stay high-density with sticky headers where needed. Forms expose validation errors inline.

## Motion
Use 150ms to 300ms transitions for hover, drawers, tabs, cards, and drag states. Canvas particles and parallax must respect reduced-motion preferences. Motion should show state or depth, not distract from task work.

## Security UI Notes
The frontend may mock roles for prototype visibility, but role permissions must be enforced server-side through Supabase Auth, RLS, and Edge Functions in production. Social linking copy must make clear parsing is client-side and consent-based.
