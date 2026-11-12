export default function Logo() {
  return (
    <div className="flex items-start gap-3">
      <svg viewBox="0 0 48 48" className="h-11 w-11 shrink-0" aria-hidden="true">
        <defs>
          <linearGradient id="lx" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" stopColor="#22d3ee" />
            <stop offset="1" stopColor="#2563eb" />
          </linearGradient>
        </defs>
        <path d="M4 6h10l10 14L34 6h10L29 27l15 15H34L24 29 14 42H4l15-15z" fill="url(#lx)" />
      </svg>
      <div className="leading-tight">
        <div className="text-2xl font-bold tracking-tight">RUNWAY X</div>
        <div className="mt-0.5 text-xs text-slate-300">Manufacturing Financial Intelligence</div>
      </div>
    </div>
  );
}
