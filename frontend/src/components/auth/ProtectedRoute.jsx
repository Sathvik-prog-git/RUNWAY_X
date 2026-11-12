import { Loader2 } from "lucide-react";
import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "./AuthContext.jsx";

export function AuthLoading() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-app-bg" role="status">
      <Loader2 className="h-6 w-6 animate-spin text-brand-sky" aria-label="Checking your session" />
    </div>
  );
}

/** Wraps private pages: signed-out visitors are sent to /login and returned here after signing in. */
export default function ProtectedRoute() {
  const { status } = useAuth();
  const location = useLocation();
  if (status === "loading") return <AuthLoading />;
  if (status === "unauthenticated") return <Navigate to="/login" replace state={{ from: location }} />;
  return <Outlet />;
}
