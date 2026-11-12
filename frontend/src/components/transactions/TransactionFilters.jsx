import { Search, X } from "lucide-react";
import { STATUSES, TYPES, EMPTY_FILTERS } from "../../utils/transactionUtils.js";
import { BTN_GHOST, FIELD } from "./fieldStyles.js";

function Field({ id, label, children, className = "" }) {
  return (
    <div className={className}>
      <label htmlFor={id} className="mb-1 block text-xs font-medium text-slate-300">{label}</label>
      {children}
    </div>
  );
}

export default function TransactionFilters({ filters, onChange, shown, total }) {
  const set = (key) => (e) => onChange({ ...filters, [key]: e.target.value });
  const active = JSON.stringify(filters) !== JSON.stringify(EMPTY_FILTERS);
  const dark = { colorScheme: "dark" }; // dark native date picker

  return (
    <div>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-[2fr_1fr_1fr_1fr_1fr]">
        <Field id="tx-search" label="Search" className="sm:col-span-2 lg:col-span-1">
          <div className="relative">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-brand-sky" />
            <input id="tx-search" type="search" value={filters.search} onChange={set("search")}
              placeholder="Transaction ID or party" className={`${FIELD} pl-9`} />
          </div>
        </Field>
        <Field id="tx-type" label="Type">
          <select id="tx-type" value={filters.type} onChange={set("type")} className={FIELD}>
            <option value="All">All types</option>
            {TYPES.map((t) => <option key={t}>{t}</option>)}
          </select>
        </Field>
        <Field id="tx-status" label="Status">
          <select id="tx-status" value={filters.status} onChange={set("status")} className={FIELD}>
            <option value="All">All statuses</option>
            {STATUSES.map((s) => <option key={s}>{s}</option>)}
          </select>
        </Field>
        <Field id="tx-from" label="Invoice date from">
          <input id="tx-from" type="date" value={filters.from} max={filters.to || undefined} onChange={set("from")} className={FIELD} style={dark} />
        </Field>
        <Field id="tx-to" label="Invoice date to">
          <input id="tx-to" type="date" value={filters.to} min={filters.from || undefined} onChange={set("to")} className={FIELD} style={dark} />
        </Field>
      </div>

      <div className="mt-3 flex flex-wrap items-center justify-between gap-2">
        <p className="text-xs text-slate-300" role="status" aria-live="polite">
          Showing {shown} of {total} transactions
        </p>
        {active && (
          <button type="button" onClick={() => onChange(EMPTY_FILTERS)} className={`${BTN_GHOST} !px-3 !py-1.5 text-xs`}>
            <X className="h-3.5 w-3.5" /> Clear filters
          </button>
        )}
      </div>
    </div>
  );
}
