import Logo from "../ui/Logo.jsx";

/**
 * Full-screen frame for signed-out pages (login now; register / reset later).
 * Uses the same app background and Logo as the dashboard. Left column shows brand
 * messaging on large screens only; on tablet/mobile only the logo remains.
 */
const POINTS = [
  "See your cash runway before it becomes a problem",
  "Know which customers are likely to pay late",
  "Make decisions backed by your own business data",
];

export default function AuthShell({ children }) {
  return (
    <div className="min-h-screen bg-app-bg">
      <div className="mx-auto grid min-h-screen w-full max-w-[1200px] items-center gap-12 px-5 py-8 sm:px-8 lg:grid-cols-[1fr_440px]">
        <section className="hidden lg:block">
          <Logo />
          <h1 className="mt-14 max-w-md text-4xl font-semibold leading-tight tracking-tight">
            Smarter Decisions. <span className="font-bold text-brand-sky">Stronger Business.</span>
          </h1>
          <p className="mt-4 max-w-md text-lg text-slate-200">
            Financial intelligence built for MSME manufacturers.
          </p>
          <ul className="mt-8 max-w-md space-y-3">
            {POINTS.map((p) => (
              <li key={p} className="flex items-center gap-3 text-sm text-slate-200">
                <span className="h-2 w-2 shrink-0 rounded-full bg-brand-cyan shadow-glow-sm" aria-hidden="true" />
                {p}
              </li>
            ))}
          </ul>
        </section>

        <div className="mx-auto w-full max-w-[440px]">
          <div className="mb-6 flex justify-center lg:hidden"><Logo /></div>
          {children}
        </div>
      </div>
    </div>
  );
}
