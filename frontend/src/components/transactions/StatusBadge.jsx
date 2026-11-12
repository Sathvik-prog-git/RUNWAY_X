const STYLES = {
  Paid: "bg-good/20 text-good",
  Pending: "bg-brand-sky/20 text-brand-sky",
  Overdue: "bg-bad/20 text-bad",
};

export default function StatusBadge({ status }) {
  return (
    <span className={`inline-block rounded-md px-2.5 py-0.5 text-xs font-medium ${STYLES[status] ?? "bg-slate-500/20 text-slate-300"}`}>
      {status}
    </span>
  );
}
