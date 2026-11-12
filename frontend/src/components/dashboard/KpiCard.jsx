import { ArrowDown, ArrowUp, CalendarDays, CreditCard, Database, Handshake } from "lucide-react";
import Sparkline from "../ui/Sparkline.jsx";

const ICONS = { database: Database, handshake: Handshake, card: CreditCard, calendar: CalendarDays };
const TONES = {
  cyan: { chip: "bg-brand-sky/20 text-brand-sky", line: "#22d3ee" },
  blue: { chip: "bg-brand-blue/25 text-brand-sky", line: "#3b82f6" },
  violet: { chip: "bg-brand-violet/25 text-violet-300", line: "#a78bfa" },
  green: { chip: "bg-good/20 text-good", line: "#10d9a0" },
};

export default function KpiCard({ label, value, change, tone = "cyan", icon, trend }) {
  const Icon = ICONS[icon] ?? Database;
  const t = TONES[tone] ?? TONES.cyan;
  const up = change >= 0;
  return (
    <article className="panel overflow-hidden p-4">
      <div className="flex items-center gap-4">
        <span className={`flex h-14 w-14 shrink-0 items-center justify-center rounded-xl ${t.chip}`}>
          <Icon className="h-7 w-7" strokeWidth={1.75} />
        </span>
        <div className="min-w-0 flex-1">
          <p className="text-sm text-slate-200">{label}</p>
          <div className="mt-1 flex items-baseline justify-between gap-2">
            <span className="text-2xl font-bold tracking-tight">{value}</span>
            <span className={`flex items-center text-xs font-semibold ${up ? "text-good" : "text-bad"}`}>
              {up ? <ArrowUp className="h-3.5 w-3.5" /> : <ArrowDown className="h-3.5 w-3.5" />}
              {Math.abs(change)}%
            </span>
          </div>
        </div>
      </div>
      <div className="mt-2"><Sparkline data={trend} color={t.line} /></div>
    </article>
  );
}
