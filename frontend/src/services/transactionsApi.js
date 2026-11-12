import { MOCK_TRANSACTIONS } from "./transactionsMock.js";

/**
 * Transactions API client.
 *
 * ── FastAPI contract (for the backend owner) ───────────────────────────────
 *  GET  /api/transactions
 *       → 200 Transaction[]            (shape: see utils/transactionUtils.js)
 *       Filtering/search/pagination are done client-side today. When data grows,
 *       accept ?search=&type=&status=&from=&to=&page=&page_size= and return
 *       { items, total } instead — only this file and TransactionsPage change.
 *
 *  POST /api/transactions/import
 *       body:  { transactions: Transaction[] }
 *       → 200 { imported: number, skipped: number }
 *       → 422 { detail: string }       (validation failure; message is shown to the user)
 *       The server must re-validate: the browser check is for convenience only.
 * ───────────────────────────────────────────────────────────────────────────
 * Flip USE_MOCK to false to use the real backend (proxied via vite.config.js).
 */
export const USE_MOCK = true;

// In-memory store so imports survive a "reload" within the session (mock mode only).
let mockStore = [...MOCK_TRANSACTIONS];
const wait = (value, ms = 250) => new Promise((resolve) => setTimeout(() => resolve(value), ms));

async function request(path, options) {
  const res = await fetch(`/api${path}`, { headers: { "Content-Type": "application/json" }, ...options });
  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try { const body = await res.json(); if (typeof body.detail === "string") detail = body.detail; } catch { /* keep default */ }
    throw new Error(detail);
  }
  return res.json();
}

export async function getTransactions() {
  if (USE_MOCK) return wait([...mockStore]);
  return request("/transactions");
}

export async function importTransactions(transactions) {
  if (USE_MOCK) {
    const known = new Set(mockStore.map((t) => t.transactionId));
    const fresh = transactions.filter((t) => !known.has(t.transactionId));
    mockStore = [...fresh, ...mockStore];
    return wait({ imported: fresh.length, skipped: transactions.length - fresh.length }, 500);
  }
  return request("/transactions/import", { method: "POST", body: JSON.stringify({ transactions }) });
}
