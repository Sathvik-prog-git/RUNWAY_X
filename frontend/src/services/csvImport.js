import { TYPES, STATUSES, deriveStatus, todayISO } from "../utils/transactionUtils.js";

/**
 * CSV validation + parsing for the transaction import. Runs fully in the browser
 * so users get instant feedback; the backend should re-validate on upload.
 */
export const MAX_FILE_BYTES = 2 * 1024 * 1024; // 2 MB
export const MAX_ROWS = 5000;

export const REQUIRED_FIELDS = ["transactionId", "party", "amount", "invoiceDate", "dueDate", "type"];
export const OPTIONAL_FIELDS = ["paymentDate", "status"];

// Accepted header spellings (after lower-casing and turning symbols into "_").
const HEADER_ALIASES = {
  transactionId: ["transaction_id", "id", "txn_id", "invoice_no", "invoice_number"],
  party: ["party", "customer_supplier", "customer", "supplier", "customer_or_supplier", "name"],
  amount: ["amount", "amount_inr", "value"],
  invoiceDate: ["invoice_date", "date"],
  dueDate: ["due_date", "due"],
  paymentDate: ["payment_date", "paid_on", "paid_date"],
  type: ["type", "transaction_type", "direction"],
  status: ["status"],
};

const TYPE_ALIASES = {
  incoming: "Incoming", income: "Incoming", receivable: "Incoming", credit: "Incoming", inflow: "Incoming", received: "Incoming",
  outgoing: "Outgoing", expense: "Outgoing", payable: "Outgoing", debit: "Outgoing", outflow: "Outgoing",
};

const normHeader = (h) => h.replace(/^\uFEFF/, "").trim().toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "");

/** Returns an error message, or null if the file looks acceptable. */
export function validateFile(file) {
  if (!file) return "No file selected.";
  if (!/\.csv$/i.test(file.name)) return "Only .csv files are supported. Export your sheet as CSV and try again.";
  const okMime = ["", "text/csv", "application/csv", "application/vnd.ms-excel", "text/plain"];
  if (!okMime.includes(file.type)) return `This file looks like "${file.type}", not a CSV.`;
  if (file.size === 0) return "The file is empty.";
  if (file.size > MAX_FILE_BYTES) return `File is too large (${(file.size / 1048576).toFixed(1)} MB). The limit is 2 MB.`;
  return null;
}

/** Minimal RFC-4180 parser: quoted fields, escaped quotes, CRLF/LF, embedded newlines. */
export function parseCsv(text) {
  const rows = [];
  let row = [], field = "", inQuotes = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (inQuotes) {
      if (c === '"') {
        if (text[i + 1] === '"') { field += '"'; i++; } else inQuotes = false;
      } else field += c;
    } else if (c === '"') inQuotes = true;
    else if (c === ",") { row.push(field); field = ""; }
    else if (c === "\n" || c === "\r") {
      if (c === "\r" && text[i + 1] === "\n") i++;
      row.push(field); field = "";
      rows.push(row); row = [];
    } else field += c;
  }
  if (field !== "" || row.length) { row.push(field); rows.push(row); }
  return { rows, unterminatedQuote: inQuotes };
}

/** Accepts YYYY-MM-DD or DD/MM/YYYY (or DD-MM-YYYY). Returns ISO or null. */
export function parseDate(raw) {
  const s = raw.trim();
  let y, m, d;
  let match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(s);
  if (match) [, y, m, d] = match;
  else if ((match = /^(\d{1,2})[/-](\d{1,2})[/-](\d{4})$/.exec(s))) [, d, m, y] = match;
  else return null;
  const dt = new Date(Date.UTC(+y, +m - 1, +d));
  if (dt.getUTCFullYear() !== +y || dt.getUTCMonth() !== +m - 1 || dt.getUTCDate() !== +d) return null;
  return `${y}-${String(m).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
}

export function parseAmount(raw) {
  const cleaned = raw.replace(/₹|inr|rs\.?|,|\s/gi, "");
  if (!/^\d+(\.\d{1,2})?$/.test(cleaned)) return null;
  const n = Number(cleaned);
  return n > 0 ? n : null;
}

/**
 * @param {string} text  raw CSV contents
 * @param {Set<string>} existingIds  IDs already in the table (to catch duplicates)
 * @returns {{ rows: object[], errors: {row:number, message:string}[], totalRows: number, fatal: string|null }}
 *   `row` in errors is the data-row number (header excluded). `fatal` set => nothing can be imported.
 */
export function parseTransactionsCsv(text, existingIds = new Set(), today = todayISO()) {
  const fail = (fatal) => ({ rows: [], errors: [], totalRows: 0, fatal });
  const { rows: raw, unterminatedQuote } = parseCsv(text);
  if (unterminatedQuote) return fail("The file has an unclosed quotation mark, so it can't be read reliably.");
  if (raw.length === 0) return fail("The file is empty.");

  // Map columns by header name
  const colIndex = {};
  raw[0].forEach((h, i) => {
    const n = normHeader(h);
    for (const [field, aliases] of Object.entries(HEADER_ALIASES)) {
      if (aliases.includes(n) && !(field in colIndex)) colIndex[field] = i;
    }
  });
  const missing = REQUIRED_FIELDS.filter((f) => !(f in colIndex));
  if (missing.length) {
    const nice = { transactionId: "transaction_id", party: "party", amount: "amount", invoiceDate: "invoice_date", dueDate: "due_date", type: "type" };
    return fail(`Missing required column(s): ${missing.map((m) => nice[m]).join(", ")}. Download the template to see the expected headers.`);
  }

  const dataRows = raw.slice(1).filter((r) => r.some((c) => c.trim() !== ""));
  if (dataRows.length === 0) return fail("The file has headers but no transaction rows.");
  if (dataRows.length > MAX_ROWS) return fail(`Too many rows (${dataRows.length}). The limit is ${MAX_ROWS} per upload.`);

  const get = (r, f) => (f in colIndex ? (r[colIndex[f]] ?? "").trim() : "");
  const seen = new Set();
  const rows = [], errors = [];

  dataRows.forEach((r, i) => {
    const n = i + 1;
    const problems = [];

    const transactionId = get(r, "transactionId");
    if (!transactionId) problems.push("transaction_id is empty");
    else if (seen.has(transactionId)) problems.push(`duplicate transaction_id "${transactionId}" in this file`);
    else if (existingIds.has(transactionId)) problems.push(`transaction_id "${transactionId}" already exists`);

    const party = get(r, "party");
    if (!party) problems.push("customer/supplier is empty");

    const amount = parseAmount(get(r, "amount"));
    if (amount === null) problems.push(`amount "${get(r, "amount")}" must be a positive number`);

    const type = TYPE_ALIASES[get(r, "type").toLowerCase()];
    if (!type) problems.push(`type "${get(r, "type")}" must be one of ${TYPES.join(" / ")}`);

    const invoiceDate = parseDate(get(r, "invoiceDate"));
    if (!invoiceDate) problems.push(`invoice_date "${get(r, "invoiceDate")}" isn't a valid date (use YYYY-MM-DD)`);
    const dueDate = parseDate(get(r, "dueDate"));
    if (!dueDate) problems.push(`due_date "${get(r, "dueDate")}" isn't a valid date (use YYYY-MM-DD)`);
    if (invoiceDate && dueDate && dueDate < invoiceDate) problems.push("due_date is before invoice_date");

    const payRaw = get(r, "paymentDate");
    const paymentDate = payRaw ? parseDate(payRaw) : null;
    if (payRaw && !paymentDate) problems.push(`payment_date "${payRaw}" isn't a valid date (use YYYY-MM-DD)`);

    let status = null;
    const statusRaw = get(r, "status");
    if (statusRaw) {
      status = STATUSES.find((s) => s.toLowerCase() === statusRaw.toLowerCase()) ?? null;
      if (!status) problems.push(`status "${statusRaw}" must be one of ${STATUSES.join(" / ")}`);
      else if (status === "Paid" && !paymentDate) problems.push("status is Paid but payment_date is empty");
      else if (status !== "Paid" && paymentDate) problems.push(`payment_date is set but status is ${status}`);
    }

    if (problems.length) {
      errors.push({ row: n, message: problems.join("; ") });
      return;
    }
    seen.add(transactionId);
    rows.push({
      transactionId, party, type, amount, invoiceDate, dueDate, paymentDate,
      status: status ?? deriveStatus({ paymentDate, dueDate }, today),
    });
  });

  return { rows, errors, totalRows: dataRows.length, fatal: null };
}

/** Template the user can download and fill in. */
export function buildTemplateCsv() {
  return [
    "transaction_id,party,type,amount,invoice_date,due_date,payment_date,status",
    "INV-2026-900,Example Customer Pvt Ltd,Incoming,150000,2026-11-01,2026-12-01,,Pending",
    "BILL-2026-900,Example Supplier Co,Outgoing,82000,2026-10-15,2026-11-14,2026-11-10,Paid",
  ].join("\n") + "\n";
}
