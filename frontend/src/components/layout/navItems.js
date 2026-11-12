import {
  LayoutDashboard, Repeat, Receipt, ClipboardList, HandCoins, Wallet,
  BrainCircuit, Factory, BarChart3, FileText, Settings,
} from "lucide-react";

// Single source of truth for sidebar + routes.
export const NAV_ITEMS = [
  { label: "Dashboard", path: "/", icon: LayoutDashboard },
  { label: "Cash Flow", path: "/cash-flow", icon: Repeat },
  { label: "Transactions", path: "/transactions", icon: Receipt },
  { label: "Orders", path: "/orders", icon: ClipboardList },
  { label: "Receivables", path: "/receivables", icon: HandCoins },
  { label: "Payables", path: "/payables", icon: Wallet },
  { label: "AI Intelligence", path: "/ai-intelligence", icon: BrainCircuit },
  { label: "Manufacturing", path: "/manufacturing", icon: Factory },
  { label: "Analytics", path: "/analytics", icon: BarChart3 },
  { label: "Reports", path: "/reports", icon: FileText },
  { label: "Settings", path: "/settings", icon: Settings },
];
