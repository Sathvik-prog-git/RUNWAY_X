import { useEffect, useRef } from "react";
import { Bell, ChevronDown, Search } from "lucide-react";
import { getUser } from "../../services/api.js";
import { useAsync } from "../../services/useAsync.js";

export default function Topbar() {
  const { data: user } = useAsync(getUser);
  const searchRef = useRef(null);

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
        <button type="button" className="flex items-center gap-2.5">
          <span className="flex h-10 w-10 items-center justify-center rounded-full bg-brand-sky text-sm font-bold text-navy-950">
            {user?.initials ?? ""}
          </span>
          <span className="hidden text-sm font-medium sm:inline">{user?.name ?? ""}</span>
          <ChevronDown className="h-4 w-4" />
        </button>
      </div>
    </header>
  );
}
