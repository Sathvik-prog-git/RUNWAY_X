# RUNWAY X — Manufacturing Financial Intelligence

Cash-flow visibility, runway simulation and AI-driven interventions for MSME manufacturers.

## Repository layout and ownership

| Folder | Owner | Status |
|---|---|---|
| `frontend/` | Frontend lead | Step 1: dashboard foundation (mock data) |
| `backend/main.py`, `schemas.py` | Backend/API lead | Placeholder |
| `backend/simulation.py`, `interventions.py` | Simulation lead | Placeholder |
| `ml/` | ML lead | Placeholder |
| `data/` | Shared | Sample CSV only |

Work in your own folder and open pull requests; avoid editing another owner's files without discussing it.

## Run the frontend

Requires Node.js 18+ (20 or 22 recommended).

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. Production check: `npm run build`.

## Frontend structure

```
frontend/src/
├── App.jsx                  route table
├── components/
│   ├── layout/              AppLayout, Sidebar, Topbar, navItems.js
│   ├── ui/                  Panel, Sparkline, Logo (shared primitives)
│   └── dashboard/           one file per dashboard widget
├── pages/                   one file per route (DashboardPage + PlaceholderPage)
└── services/                api.js (mock now, real fetch later), mockData.js, useAsync.js
```

Adding a page: create `src/pages/XPage.jsx`, then swap its `PlaceholderPage` route in `App.jsx`.
Design tokens (colors, glow, fonts) live in `frontend/tailwind.config.js`.
Components get data only through `services/api.js`, so switching to the real backend means editing that one file.
