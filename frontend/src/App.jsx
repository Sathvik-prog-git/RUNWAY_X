import { Routes, Route } from "react-router-dom";
import AppLayout from "./components/layout/AppLayout.jsx";
import DashboardPage from "./pages/DashboardPage.jsx";
import PlaceholderPage from "./pages/PlaceholderPage.jsx";
import TransactionsPage from "./pages/TransactionsPage.jsx";
import { NAV_ITEMS } from "./components/layout/navItems.js";

/**
 * Route table. Each teammate replaces PlaceholderPage for their section
 * with a real page file in src/pages/ (one file per route = no merge conflicts).
 */
export default function App() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route index element={<DashboardPage />} />
        <Route path="transactions" element={<TransactionsPage />} />
        {NAV_ITEMS.filter((n) => n.path !== "/" && n.path !== "/transactions").map((n) => (
          <Route key={n.path} path={n.path.slice(1)} element={<PlaceholderPage title={n.label} />} />
        ))}
        <Route path="*" element={<PlaceholderPage title="Page not found" />} />
      </Route>
    </Routes>
  );
}
