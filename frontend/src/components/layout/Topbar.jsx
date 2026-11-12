import { useEffect, useRef, useState } from "react";
import { Bell, LogOut, Search } from "lucide-react";
import { useAuth } from "../auth/AuthContext.jsx";

export default function Topbar() {
  const { user, signOut } = useAuth();
  const [signingOut, setSigningOut] = useState(false);
  const [signOutError, setSignOutError] = useState("");
  const searchRef = useRef(null);

  async function handleSignOut() {
    setSigningOut(true);
    setSignOutError("");
    try {
      await signOut(); // on success the route guard sends the user to /login
    } catch (err) {
      setSignOutError(err.message || "Couldn't sign out. Please try again.");
      setSigningOut(false);
    }
  }

  // Ctrl/Cmd + K focuses search, as hinted in the placeholder.
  useEffect(() => {
    const onKey = (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        searchRef.current?.focus();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  return (
    <header className="flex items-center justify-between gap-4">
      <label className="flex h-12 w-full max-w-[505px] items-center gap-3 rounded-full border border-sky-400/30 bg-navy-900/60 px-5 focus-within:border-brand-cyan">
        <Search className="h-5 w-5 text-brand-sky" />
        <input
          ref={searchRef}
          type="search"
          placeholder="Search anything... (Ctrl + K)"
          className="w-full bg-transparent text-sm text-slate-100 placeholder:text-slate-400 focus:outline-none"
        />
      </label>

      <div className="flex items-center gap-5">
        <button type="button" aria-label="Notifications, 3 unread" className="relative">
          <Bell className="h-6 w-6 text-brand-sky" />
          <span className="absolute -right-1.5 -top-1.5 flex h-4 w-4 items-center justify-center rounded-full bg-bad text-[10px] font-bold">3</span>
        </button>
        <div className="flex items-center gap-2.5">
          <span aria-hidden="true" className="flex h-10 w-10 items-center justify-center rounded-full bg-brand-sky text-sm font-bold text-navy-950">
            {user?.email?.[0]?.toUpperCase() ?? ""}
          </span>
          <span className="hidden max-w-[200px] truncate text-sm font-medium sm:inline" title={user?.email}>{user?.email ?? ""}</span>
        </div>
        <button
          type="button" onClick={handleSignOut} disabled={signingOut}
          className="flex items-center gap-2 rounded-lg border border-sky-400/30 bg-navy-900/60 px-3 py-2 text-sm font-medium text-slate-100 transition hover:border-brand-cyan disabled:opacity-50"
        >
          <LogOut className="h-4 w-4 text-brand-sky" /> <span className="hidden sm:inline">{signingOut ? "Signing out…" : "Sign out"}</span>
        </button>
        {signOutError && <span role="alert" className="text-xs text-red-300">{signOutError}</span>}
      </div>
    </header>
  );
}
