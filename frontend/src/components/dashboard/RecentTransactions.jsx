import { CreditCard, Download, ReceiptText, ShoppingCart } from "lucide-react";
import Panel from "../ui/Panel.jsx";

const ICONS = { download: Download, cart: ShoppingCart, card: CreditCard };
const inr = new Intl.NumberFormat("en-IN");

export default function RecentTransactions({ rows = [] }) {
  return (
    <Panel title="Recent Transactions" icon={ReceiptText} viewAll="/transactions">
      <div className="overflow-x-auto">
        <table className="w-full min-w-[520px] text-left text-sm">
          <thead className="text-xs text-slate-300">
            <tr className="border-b border-sky-400/15">
              <th className="py-2 font-medium">Date</th>
              <th className="py-2 font-medium">Description</th>
              <th className="py-2 font-medium">Type</th>
              <th className="py-2 font-medium">Amount</th>
              <th className="py-2 font-medium">Status</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((t) => {
              const Icon = ICONS[t.icon] ?? CreditCard;
              const income = t.amount >= 0;
              const tone = income ? "text-good" : "text-bad";
              return (
                <tr key={t.id} className="border-b border-sky-400/10 last:border-0">
                  <td className="py-2.5"><span className="flex items-center gap-2"><Icon className="h-4 w-4 text-brand-sky" />{t.date}</span></td>
                  <td className="py-2.5">{t.description}</td>
                  <td className={`py-2.5 ${tone}`}>{t.type}</td>
                  <td className={`py-2.5 font-medium ${tone}`}>{income ? "+" : "-"}₹{inr.format(Math.abs(t.amount))}</td>
                  <td className="py-2.5"><span className="rounded-md bg-good/20 px-2.5 py-0.5 text-xs font-medium text-good">{t.status}</span></td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </Panel>
  );
}
