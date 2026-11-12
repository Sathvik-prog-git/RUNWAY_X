import { Routes, Route } from "react-router-dom";
import AppLayout from "./components/layout/AppLayout.jsx";
import DashboardPage from "./pages/DashboardPage.jsx";
import PlaceholderPage from "./pages/PlaceholderPage.jsx";
import TransactionsPage from "./pages/TransactionsPage.jsx";
import LoginPage from "./pages/LoginPage.jsx";
import AuthShell from "./components/auth/AuthShell.jsx";
import { AuthProvider } from "./components/auth/AuthContext.jsx";
import ProtectedRoute from "./components/auth/ProtectedRoute.jsx";
import PublicOnlyRoute from "./components/auth/PublicOnlyRoute.jsx";
import { NAV_ITEMS } from "./components/layout/navItems.js";

// Stand-in for signed-out pages that are not built yet (register, forgot password).
const AuthPlaceholder = ({ title }) => (
  <AuthShell>
    <PlaceholderPage title={title} />
  </AuthShell>
);

/**
 * Route table. Each teammate replaces PlaceholderPage for their section
 * with a real page file in src/pages/ (one file per route = no merge conflicts).
 */
export default function App() {
  return (
    <AuthProvider>
      <Routes>
        {/* Signed-out pages: no sidebar / topbar. /login bounces signed-in users to the dashboard. */}
        <Route element={<PublicOnlyRoute />}>
          <Route path="login" element={<LoginPage />} />
        </Route>
        <Route path="register" element={<AuthPlaceholder title="Create Company Account" />} />
        <Route path="forgot-password" element={<AuthPlaceholder title="Forgot Password" />} />

        {/* Everything below requires a signed-in user; others are redirected to /login. */}
        <Route element={<ProtectedRoute />}>
          <Route element={<AppLayout />}>
            <Route index element={<DashboardPage />} />
            <Route path="transactions" element={<TransactionsPage />} />
            {NAV_ITEMS.filter((n) => n.path !== "/" && n.path !== "/transactions").map((n) => (
              <Route key={n.path} path={n.path.slice(1)} element={<PlaceholderPage title={n.label} />} />
            ))}
            <Route path="*" element={<PlaceholderPage title="Page not found" />} />
          </Route>
        </Route>
      </Routes>
    </AuthProvider>
  );
}
