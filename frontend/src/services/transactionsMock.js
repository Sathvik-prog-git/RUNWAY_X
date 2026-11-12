/**
 * ⚠️ MOCK DATA — fictional parties and amounts, for UI development only.
 * Delete this file (and the mock branch in transactionsApi.js) once the
 * FastAPI endpoints are live. Dates are fixed, so "Overdue" rows are stored
 * explicitly rather than computed from today's date.
 */
const t = (transactionId, party, type, amount, invoiceDate, dueDate, paymentDate, status) =>
  ({ transactionId, party, type, amount, invoiceDate, dueDate, paymentDate, status });

const IN = "Incoming", OUT = "Outgoing";

export const MOCK_TRANSACTIONS = [
  t("INV-2026-001", "Shree Auto Components Pvt Ltd", IN, 250000, "2026-09-02", "2026-10-02", "2026-10-01", "Paid"),
  t("INV-2026-002", "Bharat Fasteners Ltd", IN, 185000, "2026-09-10", "2026-10-10", "2026-10-14", "Paid"),
  t("INV-2026-003", "Kaveri Castings", IN, 420000, "2026-09-18", "2026-10-18", null, "Overdue"),
  t("INV-2026-004", "Deccan Polymers", IN, 96500, "2026-10-01", "2026-10-31", null, "Overdue"),
  t("INV-2026-005", "Rao Engineering Works", IN, 312000, "2026-10-05", "2026-11-04", "2026-11-03", "Paid"),
  t("INV-2026-006", "Sri Lakshmi Textiles", IN, 148000, "2026-10-12", "2026-11-11", null, "Overdue"),
  t("INV-2026-007", "Nagarjuna Tools", IN, 275000, "2026-10-20", "2026-11-19", null, "Pending"),
  t("INV-2026-008", "Hyderabad Bearings Co", IN, 530000, "2026-10-28", "2026-11-27", null, "Pending"),
  t("INV-2026-009", "Mahesh Packaging", IN, 88000, "2026-11-02", "2026-12-02", null, "Pending"),
  t("INV-2026-010", "Krishna Valves", IN, 365000, "2026-11-06", "2026-12-06", null, "Pending"),
  t("INV-2026-011", "Shree Auto Components Pvt Ltd", IN, 210000, "2026-11-09", "2026-12-09", null, "Pending"),
  t("INV-2026-012", "Deccan Polymers", IN, 72000, "2026-08-20", "2026-09-19", "2026-09-25", "Paid"),
  t("BILL-2026-101", "Godavari Steel Traders", OUT, 380000, "2026-09-05", "2026-10-05", "2026-10-04", "Paid"),
  t("BILL-2026-102", "Andhra Alloys Pvt Ltd", OUT, 210000, "2026-09-22", "2026-10-22", "2026-10-21", "Paid"),
  t("BILL-2026-103", "Sunrise Packaging Supplies", OUT, 64000, "2026-10-02", "2026-11-01", null, "Overdue"),
  t("BILL-2026-104", "Vizag Lubricants", OUT, 47500, "2026-10-08", "2026-11-07", null, "Overdue"),
  t("BILL-2026-105", "Metro Power Distribution", OUT, 118000, "2026-10-15", "2026-11-14", null, "Pending"),
  t("BILL-2026-106", "Godavari Steel Traders", OUT, 450000, "2026-10-25", "2026-11-24", null, "Pending"),
  t("BILL-2026-107", "Andhra Alloys Pvt Ltd", OUT, 275000, "2026-11-01", "2026-12-01", null, "Pending"),
  t("BILL-2026-108", "Precision Tooling Services", OUT, 92000, "2026-11-05", "2026-11-20", null, "Pending"),
  t("BILL-2026-109", "Coastal Logistics", OUT, 56000, "2026-09-28", "2026-10-28", "2026-10-27", "Paid"),
  t("BILL-2026-110", "Payroll - October", OUT, 640000, "2026-10-31", "2026-10-31", "2026-10-31", "Paid"),
  t("BILL-2026-111", "Vizag Lubricants", OUT, 39000, "2026-08-30", "2026-09-29", "2026-09-28", "Paid"),
];
