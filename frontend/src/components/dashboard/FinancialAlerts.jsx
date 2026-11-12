import { AlertTriangle, Info, OctagonAlert } from "lucide-react";
import Panel from "../ui/Panel.jsx";

const LEVELS = {
  danger: { icon: OctagonAlert, color: "text-bad" },
  warning: { icon: AlertTriangle, color: "text-warn" },
  info: { icon: Info, color: "text-brand-sky" },
};

export default function FinancialAlerts({ alerts = [] }) {
  return (
    <Panel title="Financial Alerts" viewAll="/analytics">
      <ul className="divide-y divide-sky-400/15">
        {alerts.map((a) => {
          const { icon: Icon, color } = LEVELS[a.level] ?? LEVELS.info;
          return (
            <li key={a.id} className="flex items-center gap-4 py-3 first:pt-0">
              <Icon className={`h-8 w-8 shrink-0 ${color}`} strokeWidth={1.75} />
              <div>
                <p className="text-sm font-semibold">{a.title}</p>
                <p className="text-xs text-slate-300">{a.detail}</p>
              </div>
            </li>
          );
        })}
      </ul>
    </Panel>
  );
}
