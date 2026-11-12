import { CalendarCheck, TrendingUp } from "lucide-react";
import Panel from "../ui/Panel.jsx";

export default function HealthScore({ score = 0, label = "", change = 0 }) {
  const r = 70;
  const c = 2 * Math.PI * r;
  return (
    <Panel title="Business Health Score" icon={CalendarCheck}>
      <div className="flex flex-col items-center">
        <div className="relative h-44 w-44">
          <svg viewBox="0 0 180 180" className="h-full w-full -rotate-90" role="img" aria-label={`Health score ${score} percent`}>
            <defs>
              <linearGradient id="ring" x1="0" y1="0" x2="1" y2="1">
                <stop offset="0" stopColor="#22d3ee" />
                <stop offset="1" stopColor="#10d9a0" />
              </linearGradient>
            </defs>
            <circle cx="90" cy="90" r={r} fill="none" stroke="rgba(56,189,248,0.15)" strokeWidth="12" />
            <circle
              cx="90" cy="90" r={r} fill="none" stroke="url(#ring)" strokeWidth="12" strokeLinecap="round"
              strokeDasharray={c} strokeDashoffset={c * (1 - score / 100)}
            />
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className="text-4xl font-bold">{score}%</span>
            <span className="text-sm font-medium text-good">{label}</span>
          </div>
        </div>
        <p className="mt-3 flex items-center gap-2 text-sm font-semibold text-good">
          <TrendingUp className="h-4 w-4" /> {change}%
        </p>
        <p className="text-xs text-slate-300">vs last month</p>
      </div>
    </Panel>
  );
}
