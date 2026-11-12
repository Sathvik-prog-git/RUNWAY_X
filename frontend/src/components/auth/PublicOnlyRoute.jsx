import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "./AuthContext.jsx";
import { AuthLoading } from "./ProtectedRoute.jsx";

/** Only a same-site path is accepted as a return target (guards against open redirects). */
function safeTarget(from) {
  const path = from ? `${from.pathname ?? ""}${from.search ?? ""}` : "";
  return path.startsWith("/") && !path.startsWith("//") && !path.startsWith("/login") ? path : "/";
}

/** Wraps /login: people who are already signed in go to the dashboard (or the page they came from). */
export default function PublicOnlyRoute() {
  const { status } = useAuth();
  const location = useLocation();
  if (status === "loading") return <AuthLoading />;
  if (status === "authenticated") return <Navigate to={safeTarget(location.state?.from)} replace />;
  return <Outlet />;
}
