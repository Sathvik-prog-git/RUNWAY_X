import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { BarChart3, ChevronDown } from "lucide-react";
import Panel from "../ui/Panel.jsx";

const AXIS = { fill: "#cbd5e1", fontSize: 12 };

export default function CashFlowChart({ data = [] }) {
  return (
    <Panel
      title="Cash Flow Performance"
      icon={BarChart3}
      action={
        <button type="button" className="flex items-center gap-2 rounded-lg border border-sky-400/30 bg-navy-900/60 px-3 py-1.5 text-xs">
          Last 6 Months <ChevronDown className="h-3.5 w-3.5" />
        </button>
      }
    >
      <div className="mb-2 flex justify-center gap-5 text-xs text-slate-200">
        <span className="flex items-center gap-2"><i className="h-2 w-2 rounded-full bg-brand-sky" />Income</span>
        <span className="flex items-center gap-2"><i className="h-2 w-2 rounded-full bg-brand-violet" />Expenses</span>
      </div>
      <div className="h-[230px]" role="img" aria-label="Income and expenses over the last six months">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
            <defs>
              <linearGradient id="gInc" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0" stopColor="#38bdf8" stopOpacity={0.55} />
                <stop offset="1" stopColor="#2563eb" stopOpacity={0.05} />
              </linearGradient>
              <linearGradient id="gExp" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0" stopColor="#8b5cf6" stopOpacity={0.5} />
                <stop offset="1" stopColor="#4c1d95" stopOpacity={0.05} />
              </linearGradient>
            </defs>
            <CartesianGrid vertical={false} stroke="rgba(148,163,184,0.12)" />
            <XAxis dataKey="month" tick={AXIS} axisLine={false} tickLine={false} />
            <YAxis
              domain={[0, 60]}
              ticks={[0, 20, 40, 60]}
              tickFormatter={(v) => `₹${v}${v ? "L" : ""}`}
              tick={AXIS}
              axisLine={false}
              tickLine={false}
              width={48}
            />
            <Tooltip
              formatter={(v, n) => [`₹${v} L`, n === "income" ? "Income" : "Expenses"]}
              contentStyle={{ background: "#050d22", border: "1px solid rgba(56,189,248,0.4)", borderRadius: 8, color: "#fff" }}
            />
            <Area type="monotone" dataKey="income" stroke="#38bdf8" strokeWidth={2} fill="url(#gInc)" dot={{ r: 3, fill: "#38bdf8" }} />
            <Area type="monotone" dataKey="expenses" stroke="#a78bfa" strokeWidth={2} fill="url(#gExp)" dot={{ r: 3, fill: "#a78bfa" }} />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </Panel>
  );
}
