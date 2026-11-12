import WelcomeBanner from "../components/dashboard/WelcomeBanner.jsx";
import KpiCard from "../components/dashboard/KpiCard.jsx";
import CashFlowChart from "../components/dashboard/CashFlowChart.jsx";
import HealthScore from "../components/dashboard/HealthScore.jsx";
import FinancialAlerts from "../components/dashboard/FinancialAlerts.jsx";
import RecentTransactions from "../components/dashboard/RecentTransactions.jsx";
import QuickActions from "../components/dashboard/QuickActions.jsx";
import { useAsync } from "../services/useAsync.js";
import {
  getUser, getKpis, getCashFlow, getHealthScore, getAlerts, getRecentTransactions, getQuickActions,
} from "../services/api.js";

export default function DashboardPage() {
  const user = useAsync(getUser).data;
  const kpis = useAsync(getKpis).data ?? [];
  const cashFlow = useAsync(getCashFlow).data ?? [];
  const health = useAsync(getHealthScore).data;
  const alerts = useAsync(getAlerts).data ?? [];
  const txns = useAsync(getRecentTransactions).data ?? [];
  const actions = useAsync(getQuickActions).data ?? [];

  return (
    <div className="space-y-5">
      <WelcomeBanner name={user?.firstName} />

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {kpis.map((k) => <KpiCard key={k.id} {...k} />)}
      </div>

      <div className="grid gap-4 xl:grid-cols-[2fr_1fr_1fr]">
        <CashFlowChart data={cashFlow} />
        {health && <HealthScore {...health} />}
        <FinancialAlerts alerts={alerts} />
      </div>

      <div className="grid gap-4 xl:grid-cols-[1.4fr_1fr]">
        <RecentTransactions rows={txns} />
        <QuickActions actions={actions} />
      </div>
    </div>
  );
}
