import { passwordStrength } from "../../utils/registerValidation.js";

const BAR = ["bg-slate-600/50", "bg-bad", "bg-warn", "bg-brand-sky", "bg-good"];

/** Four-segment strength bar with a text label (text, not just colour, so it is accessible). */
export default function PasswordStrengthMeter({ password, email, fullName }) {
  const { score, label, tips } = passwordStrength(password, email, fullName);
  if (!password) return null;
  return (
    <div className="mt-2" aria-live="polite">
      <div className="flex gap-1.5" aria-hidden="true">
        {[1, 2, 3, 4].map((i) => (
          <span key={i} className={`h-1.5 flex-1 rounded-full ${i <= score ? BAR[score] : "bg-slate-600/40"}`} />
        ))}
      </div>
      <p className="mt-1.5 text-xs text-slate-300">
        Password strength: <span className="font-semibold text-slate-100">{label}</span>
        {tips.length > 0 && <span className="text-slate-400"> — try: {tips.join("; ")}</span>}
      </p>
    </div>
  );
}
