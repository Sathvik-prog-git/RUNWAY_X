// Mock data mirroring the dashboard reference. Replaced by real API calls in services/api.js.
export const kpis = [
  { id: "cash", label: "Cash Balance", value: "₹24.8 L", change: 12.5, tone: "cyan", icon: "database", trend: [4, 5, 4.5, 6, 5.5, 7, 6.5, 8, 9] },
  { id: "recv", label: "Receivables", value: "₹12.5 L", change: 8.2, tone: "blue", icon: "handshake", trend: [3, 4, 3.5, 5, 4, 6, 5, 7, 8] },
  { id: "pay", label: "Payables", value: "₹8.2 L", change: -5.1, tone: "violet", icon: "card", trend: [6, 5, 6.5, 5, 5.5, 4, 5, 3.5, 4] },
  { id: "runway", label: "Cash Runway", value: "42 Days", change: 6.3, tone: "green", icon: "calendar", trend: [3, 4, 3.5, 5, 4.5, 6, 5, 7, 7.5] },
];

export const cashFlow = [
  { month: "Jun", income: 27, expenses: 14 },
  { month: "Jul", income: 30, expenses: 19 },
  { month: "Aug", income: 38, expenses: 23 },
  { month: "Sep", income: 36, expenses: 21 },
  { month: "Oct", income: 48.5, expenses: 30 },
  { month: "Nov", income: 44, expenses: 30 },
];

export const healthScore = { score: 92, label: "Excellent", change: 4 };

export const alerts = [
  { id: 1, level: "danger", title: "Payable Due Soon", detail: "₹2.5 L • Due in 3 days" },
  { id: 2, level: "warning", title: "Receivable Overdue", detail: "₹1.8 L • 7 days overdue" },
  { id: 3, level: "info", title: "Cash Flow Forecast", detail: "May cash flow may drop by 18% next month" },
];

export const transactions = [
  { id: 1, date: "Apr 30, 2025", description: "Customer Payment", type: "Income", amount: 250000, status: "Cleared", icon: "download" },
  { id: 2, date: "Apr 29, 2025", description: "Raw Material Purchase", type: "Expense", amount: -180000, status: "Cleared", icon: "cart" },
  { id: 3, date: "Apr 28, 2025", description: "Supplier Payment", type: "Expense", amount: -120000, status: "Cleared", icon: "card" },
];

export const quickActions = [
  { id: "upload", label: "Upload Data", icon: "upload", to: "/transactions" },
  { id: "reports", label: "View Reports", icon: "chart", to: "/reports" },
  { id: "ai", label: "Ask AI", icon: "sparkles", to: "/ai-intelligence" },
  { id: "orders", label: "Check Orders", icon: "package", to: "/orders" },
];

export const currentUser = { name: "John Doe", firstName: "John", initials: "JD" };
