/**
 * Pure helpers for the Transactions feature (no React, no network).
 *
 * Transaction shape (also the contract for the FastAPI backend):
 * {
 *   transactionId: string,        // e.g. "INV-2026-001"
 *   party: string,                // customer (incoming) or supplier (outgoing)
 *   type: "Incoming" | "Outgoing",
 *   amount: number,               // INR, always positive; direction comes from `type`
 *   invoiceDate: "YYYY-MM-DD",
 *   dueDate: "YYYY-MM-DD",
 *   paymentDate: "YYYY-MM-DD" | null,
 *   status: "Paid" | "Pending" | "Overdue"
 * }
 */
export const TYPES = ["Incoming", "Outgoing"];
export const STATUSES = ["Paid", "Pending", "Overdue"];

const inr = new Intl.NumberFormat("en-IN");
const MS_PER_DAY = 86_400_000;

export const formatINR = (n) => `₹${inr.format(n)}`;

/** Compact lakh/crore style used on the dashboard, e.g. ₹12.5 L */
export function formatINRCompact(n) {
  const abs = Math.abs(n);
  if (abs >= 1e7) return `₹${(n / 1e7).toFixed(2)} Cr`;
  if (abs >= 1e5) return `₹${(n / 1e5).toFixed(1)} L`;
  return formatINR(n);
}

export function formatDate(iso) {
  if (!iso) return "—";
  return new Date(`${iso}T00:00:00Z`).toLocaleDateString("en-IN", {
    day: "2-digit", month: "short", year: "numeric", timeZone: "UTC",
  });
}

/** Today as YYYY-MM-DD in the user's local timezone. */
export function todayISO(now = new Date()) {
  const p = (n) => String(n).padStart(2, "0");
  return `${now.getFullYear()}-${p(now.getMonth() + 1)}-${p(now.getDate())}`;
}

/** Whole days from isoA to isoB (positive when B is later). */
export function daysBetween(isoA, isoB) {
  return Math.round((Date.parse(`${isoB}T00:00:00Z`) - Date.parse(`${isoA}T00:00:00Z`)) / MS_PER_DAY);
}

/** Status when the source data doesn't provide one. */
export function deriveStatus({ paymentDate, dueDate }, today = todayISO()) {
  if (paymentDate) return "Paid";
  return dueDate < today ? "Overdue" : "Pending";
}

/** Totals for the summary cards. Computed over ALL transactions, not the filtered view. */
export function summarize(list) {
  const out = {
    total: { count: list.length },
    incoming: { count: 0, amount: 0 },
    outgoing: { count: 0, amount: 0 },
    overdue: { count: 0, amount: 0 },
  };
  for (const t of list) {
    const bucket = t.type === "Incoming" ? out.incoming : out.outgoing;
    bucket.count += 1;
    bucket.amount += t.amount;
    if (t.status === "Overdue") {
      out.overdue.count += 1;
      out.overdue.amount += t.amount;
    }
  }
  return out;
}

export const EMPTY_FILTERS = { search: "", type: "All", status: "All", from: "", to: "" };

/** Filters apply to invoice date for the from/to range. */
export function filterTransactions(list, f) {
  const q = f.search.trim().toLowerCase();
  return list.filter((t) => {
    if (q && !t.transactionId.toLowerCase().includes(q) && !t.party.toLowerCase().includes(q)) return false;
    if (f.type !== "All" && t.type !== f.type) return false;
    if (f.status !== "All" && t.status !== f.status) return false;
    if (f.from && t.invoiceDate < f.from) return false;
    if (f.to && t.invoiceDate > f.to) return false;
    return true;
  });
}

export const sortByInvoiceDateDesc = (list) =>
  [...list].sort((a, b) => b.invoiceDate.localeCompare(a.invoiceDate) || a.transactionId.localeCompare(b.transactionId));
