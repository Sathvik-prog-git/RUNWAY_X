import { AlertTriangle, ArrowDownLeft, ArrowUpRight, Receipt } from "lucide-react";
import { formatINRCompact, summarize } from "../../utils/transactionUtils.js";

const TONES = {
  cyan: "bg-brand-sky/20 text-brand-sky",
  green: "bg-good/20 text-good",
  violet: "bg-brand-violet/25 text-violet-300",
  red: "bg-bad/20 text-bad",
};

function Card({ icon: Icon, tone, label, value, sub, onClick }) {
  const Wrapper = onClick ? "button" : "article";
  return (
    <Wrapper
      type={onClick ? "button" : undefined}
      onClick={onClick}
      title={onClick ? "Show only overdue transactions" : undefined}
      className={`panel flex items-center gap-4 p-4 text-left ${onClick ? "transition hover:border-brand-cyan" : ""}`}
    >
      <span className={`flex h-14 w-14 shrink-0 items-center justify-center rounded-xl ${TONES[tone]}`}>
        <Icon className="h-7 w-7" strokeWidth={1.75} />
      </span>
      <div className="min-w-0">
        <p className="text-sm text-slate-200">{label}</p>
        <p className="mt-0.5 truncate text-2xl font-bold tracking-tight">{value}</p>
        <p className="text-xs text-slate-300">{sub}</p>
      </div>
    </Wrapper>
  );
}

/** Totals cover every transaction, regardless of the table filters below. */
export default function SummaryCards({ transactions, onSelectOverdue }) {
  const s = summarize(transactions);
  const n = (c) => `${c} transaction${c === 1 ? "" : "s"}`;
  return (
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <Card icon={Receipt} tone="cyan" label="Total Transactions" value={s.total.count} sub="Incoming and outgoing" />
      <Card icon={ArrowDownLeft} tone="green" label="Incoming Payments" value={formatINRCompact(s.incoming.amount)} sub={n(s.incoming.count)} />
      <Card icon={ArrowUpRight} tone="violet" label="Outgoing Payments" value={formatINRCompact(s.outgoing.amount)} sub={n(s.outgoing.count)} />
      <Card icon={AlertTriangle} tone="red" label="Overdue" value={s.overdue.count} sub={`${formatINRCompact(s.overdue.amount)} past due date`} onClick={s.overdue.count ? onSelectOverdue : undefined} />
    </div>
  );
}
