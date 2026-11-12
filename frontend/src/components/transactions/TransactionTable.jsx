import { useEffect, useState } from "react";
import { ArrowDownLeft, ArrowUpRight, ChevronLeft, ChevronRight, SearchX } from "lucide-react";
import StatusBadge from "./StatusBadge.jsx";
import { BTN_GHOST } from "./fieldStyles.js";
import { daysBetween, formatDate, formatINR, todayISO } from "../../utils/transactionUtils.js";

const PAGE_SIZE = 10;

function TypeLabel({ type }) {
  const incoming = type === "Incoming";
  const Icon = incoming ? ArrowDownLeft : ArrowUpRight;
  return (
    <span className={`inline-flex items-center gap-1.5 ${incoming ? "text-good" : "text-violet-300"}`}>
      <Icon className="h-4 w-4" aria-hidden="true" /> {type}
    </span>
  );
}

const Amount = ({ t }) => (
  <span className={`font-medium ${t.type === "Incoming" ? "text-good" : "text-bad"}`}>
    {t.type === "Incoming" ? "+" : "-"}{formatINR(t.amount)}
  </span>
);

/** "Due 04 Nov 2026" plus "8 days late" for overdue rows. */
function DueDate({ t, today }) {
  const late = t.status === "Overdue" ? daysBetween(t.dueDate, today) : 0;
  return (
    <>
      <span className={t.status === "Overdue" ? "text-bad" : ""}>{formatDate(t.dueDate)}</span>
      {late > 0 && <span className="ml-1.5 text-xs text-bad/80">{late}d late</span>}
    </>
  );
}

export default function TransactionTable({ rows, hasAnyData, onClearFilters }) {
  const [page, setPage] = useState(1);
  const today = todayISO();
  const pages = Math.max(1, Math.ceil(rows.length / PAGE_SIZE));

  useEffect(() => setPage(1), [rows]);          // new filter result → back to page 1
  const current = Math.min(page, pages);
  const slice = rows.slice((current - 1) * PAGE_SIZE, current * PAGE_SIZE);

  if (rows.length === 0) {
    return (
      <div className="flex flex-col items-center gap-3 py-12 text-center">
        <SearchX className="h-10 w-10 text-brand-sky" strokeWidth={1.5} />
        <p className="font-medium">{hasAnyData ? "No transactions match these filters" : "No transactions yet"}</p>
        <p className="max-w-sm text-sm text-slate-300">
          {hasAnyData ? "Try a different search or widen the date range." : "Upload a CSV to add your first transactions."}
        </p>
        {hasAnyData && <button type="button" onClick={onClearFilters} className={BTN_GHOST}>Clear filters</button>}
      </div>
    );
  }

  return (
    <div>
      {/* Desktop / tablet table */}
      <div className="hidden overflow-x-auto md:block">
        <table className="w-full min-w-[860px] text-left text-sm">
          <thead className="text-xs text-slate-300">
            <tr className="border-b border-sky-400/15">
              {["Transaction ID", "Customer / Supplier", "Type", "Amount", "Invoice date", "Due date", "Payment date", "Status"].map((h) => (
                <th key={h} scope="col" className="whitespace-nowrap py-2 pr-4 font-medium">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {slice.map((t) => (
              <tr key={t.transactionId} className="border-b border-sky-400/10 last:border-0 hover:bg-white/[0.03]">
                <td className="whitespace-nowrap py-3 pr-4 font-medium">{t.transactionId}</td>
                <td className="py-3 pr-4">{t.party}</td>
                <td className="whitespace-nowrap py-3 pr-4"><TypeLabel type={t.type} /></td>
                <td className="whitespace-nowrap py-3 pr-4"><Amount t={t} /></td>
                <td className="whitespace-nowrap py-3 pr-4 text-slate-200">{formatDate(t.invoiceDate)}</td>
                <td className="whitespace-nowrap py-3 pr-4"><DueDate t={t} today={today} /></td>
                <td className="whitespace-nowrap py-3 pr-4 text-slate-200">{formatDate(t.paymentDate)}</td>
                <td className="py-3"><StatusBadge status={t.status} /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Mobile cards */}
      <ul className="space-y-3 md:hidden">
        {slice.map((t) => (
          <li key={t.transactionId} className="rounded-xl border border-sky-400/20 bg-navy-900/50 p-3">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <p className="text-sm font-semibold">{t.transactionId}</p>
                <p className="truncate text-xs text-slate-300">{t.party}</p>
              </div>
              <StatusBadge status={t.status} />
            </div>
            <div className="mt-2 flex items-center justify-between text-sm">
              <TypeLabel type={t.type} /> <Amount t={t} />
            </div>
            <dl className="mt-2 grid grid-cols-3 gap-2 text-xs">
              <div><dt className="text-slate-400">Invoice</dt><dd>{formatDate(t.invoiceDate)}</dd></div>
              <div><dt className="text-slate-400">Due</dt><dd><DueDate t={t} today={today} /></dd></div>
              <div><dt className="text-slate-400">Paid</dt><dd>{formatDate(t.paymentDate)}</dd></div>
            </dl>
          </li>
        ))}
      </ul>

      {pages > 1 && (
        <nav className="mt-4 flex items-center justify-between" aria-label="Pagination">
          <button type="button" className={BTN_GHOST} disabled={current === 1} onClick={() => setPage(current - 1)}>
            <ChevronLeft className="h-4 w-4" /> Previous
          </button>
          <span className="text-xs text-slate-300">Page {current} of {pages}</span>
          <button type="button" className={BTN_GHOST} disabled={current === pages} onClick={() => setPage(current + 1)}>
            Next <ChevronRight className="h-4 w-4" />
          </button>
        </nav>
      )}
    </div>
  );
}
