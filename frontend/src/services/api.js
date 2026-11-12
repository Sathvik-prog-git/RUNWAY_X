import * as mock from "./mockData.js";

/**
 * API client. Every function returns a Promise so components never care
 * whether data is mocked or real. When the backend exists (Step 2), swap the
 * body of a function for a real fetch to /api/... — component code stays unchanged.
 */
const USE_MOCK = true;
const delay = (data, ms = 150) => new Promise((r) => setTimeout(() => r(data), ms));

async function get(path, mockValue) {
  if (USE_MOCK) return delay(mockValue);
  const res = await fetch(`/api${path}`);
  if (!res.ok) throw new Error(`GET ${path} failed: ${res.status}`);
  return res.json();
}

export const getUser = () => get("/me", mock.currentUser);
export const getKpis = () => get("/dashboard/kpis", mock.kpis);
export const getCashFlow = () => get("/dashboard/cash-flow", mock.cashFlow);
export const getHealthScore = () => get("/dashboard/health-score", mock.healthScore);
export const getAlerts = () => get("/dashboard/alerts", mock.alerts);
export const getRecentTransactions = () => get("/transactions/recent", mock.transactions);
export const getQuickActions = () => get("/dashboard/quick-actions", mock.quickActions);
