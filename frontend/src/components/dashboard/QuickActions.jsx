import { BarChart3, CloudUpload, Package, Sparkles, Zap } from "lucide-react";
import { Link } from "react-router-dom";
import Panel from "../ui/Panel.jsx";

const ICONS = { upload: CloudUpload, chart: BarChart3, sparkles: Sparkles, package: Package };

export default function QuickActions({ actions = [] }) {
  return (
    <Panel title="Quick Actions" icon={Zap}>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {actions.map((a) => {
          const Icon = ICONS[a.icon] ?? Sparkles;
          return (
            <Link
              key={a.id}
              to={a.to}
              className="flex flex-col items-center gap-2 rounded-xl border border-sky-400/25 bg-navy-800/60 px-2 py-4 text-xs font-medium transition hover:border-brand-cyan hover:shadow-glow-sm"
            >
              <Icon className="h-7 w-7 text-brand-sky" strokeWidth={1.75} />
              {a.label}
            </Link>
          );
        })}
      </div>
    </Panel>
  );
}
