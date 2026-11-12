import { NavLink } from "react-router-dom";
import { ArrowUp } from "lucide-react";
import Logo from "../ui/Logo.jsx";
import { NAV_ITEMS } from "./navItems.js";

export default function Sidebar() {
  return (
    <aside className="hidden w-[270px] shrink-0 flex-col border-r border-sky-400/20 bg-navy-900/70 px-4 py-6 lg:flex">
      <div className="px-2"><Logo /></div>

      <nav className="mt-8 flex-1 space-y-1.5 overflow-y-auto" aria-label="Main">
        {NAV_ITEMS.map(({ label, path, icon: Icon }) => (
          <NavLink
            key={path}
            to={path}
            end={path === "/"}
            className={({ isActive }) =>
              `flex items-center gap-4 rounded-xl px-4 py-2.5 text-sm font-medium transition-colors ${
                isActive
                  ? "bg-nav-active text-white shadow-glow"
                  : "text-slate-300 hover:bg-white/5 hover:text-white"
              }`
            }
          >
            <Icon className="h-5 w-5 text-brand-sky" strokeWidth={1.75} />
            {label}
          </NavLink>
        ))}
      </nav>

      <div className="panel relative mt-4 overflow-hidden p-4">
        <div className="absolute -right-6 -top-6 h-28 w-28 rounded-full bg-brand-blue/30 blur-2xl" aria-hidden="true" />
        <p className="relative max-w-[150px] text-[15px] font-semibold leading-snug">
          Smarter Decisions. Stronger Business.
        </p>
        <button
          type="button"
          aria-label="Learn more"
          className="relative ml-auto mt-6 flex h-9 w-9 items-center justify-center rounded-full bg-brand-blue shadow-glow-sm hover:bg-brand-sky"
        >
          <ArrowUp className="h-4 w-4" />
        </button>
      </div>
    </aside>
  );
}
