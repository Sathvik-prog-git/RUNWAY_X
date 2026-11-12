import { Sparkles } from "lucide-react";

/** Greeting + decorative factory skyline (pure SVG, no image assets needed). */
export default function WelcomeBanner({ name = "John" }) {
  return (
    <section className="relative overflow-hidden rounded-2xl py-2">
      <svg className="pointer-events-none absolute bottom-0 right-0 hidden h-full w-[55%] opacity-80 md:block" viewBox="0 0 600 200" preserveAspectRatio="xMaxYMax slice" aria-hidden="true">
        <defs>
          <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="#2563eb" stopOpacity="0" />
            <stop offset="1" stopColor="#0ea5e9" stopOpacity="0.35" />
          </linearGradient>
        </defs>
        <rect width="600" height="200" fill="url(#sky)" />
        <g fill="#0a1d4a" stroke="#38bdf8" strokeOpacity="0.5">
          <rect x="120" y="110" width="330" height="90" />
          <rect x="250" y="70" width="110" height="40" />
          <rect x="470" y="30" width="14" height="170" />
          <rect x="500" y="50" width="12" height="150" />
          <rect x="380" y="20" width="16" height="90" />
        </g>
        <g fill="#7dd3fc" opacity="0.8">
          {Array.from({ length: 22 }).map((_, i) => (
            <rect key={`a${i}`} x={135 + i * 14} y={130} width="6" height="4" />
          ))}
          {Array.from({ length: 22 }).map((_, i) => (
            <rect key={`b${i}`} x={135 + i * 14} y={155} width="6" height="4" />
          ))}
        </g>
      </svg>

      <div className="relative">
        <span className="inline-flex items-center gap-2 rounded-lg border border-sky-400/30 bg-navy-900/60 px-3 py-1.5 text-xs font-medium text-brand-sky">
          <Sparkles className="h-3.5 w-3.5" /> Welcome to RUNWAY X
        </span>
        <h1 className="mt-4 text-4xl font-semibold tracking-tight">
          Welcome back, <span className="font-bold text-brand-sky">{name}!</span>
        </h1>
        <p className="mt-2 text-lg text-slate-200">Here's your manufacturing financial overview</p>
      </div>
    </section>
  );
}
