import { useState } from "react";
import { Link } from "react-router-dom";
import { AlertCircle, Eye, EyeOff, Loader2, Lock, Mail, ShieldCheck } from "lucide-react";
import AuthShell from "../components/auth/AuthShell.jsx";
import { BTN_PRIMARY, FIELD } from "../components/transactions/fieldStyles.js";
import { useAuth } from "../components/auth/AuthContext.jsx";

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

function validate({ email, password }) {
  const errors = {};
  if (!email.trim()) errors.email = "Enter your email address.";
  else if (!EMAIL_RE.test(email.trim())) errors.email = "Enter a valid email address, like name@company.com.";
  if (!password) errors.password = "Enter your password.";
  return errors;
}

export default function LoginPage() {
  const [values, setValues] = useState({ email: "", password: "" });
  const [remember, setRemember] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [touched, setTouched] = useState({});
  const [submitError, setSubmitError] = useState("");
  const [loading, setLoading] = useState(false);
  const { signIn, error: sessionError } = useAuth();

  const errors = validate(values);
  const show = (field) => touched[field] && errors[field];

  const set = (field) => (e) => {
    setValues((v) => ({ ...v, [field]: e.target.value }));
    setSubmitError("");
  };
  const blur = (field) => () => setTouched((t) => ({ ...t, [field]: true }));

  async function onSubmit(e) {
    e.preventDefault();
    setTouched({ email: true, password: true });
    setSubmitError("");
    if (Object.keys(errors).length) return;
    setLoading(true);
    try {
      await signIn({ email: values.email.trim(), password: values.password, remember });
      // On success the auth state changes and <PublicOnlyRoute> redirects to the dashboard (or the page the user came from).
    } catch (err) {
      setSubmitError(err.message || "We couldn't sign you in. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <AuthShell>
      <section className="panel p-6 sm:p-8" aria-labelledby="login-title">
        <h1 id="login-title" className="text-3xl font-semibold tracking-tight">Welcome back</h1>
        <p className="mt-1.5 text-sm text-slate-200">Sign in to your company's financial overview.</p>

        {(submitError || sessionError) && (
          <p role="alert" className="mt-5 flex items-start gap-2 rounded-lg border border-bad/40 bg-bad/10 p-3 text-sm text-red-200">
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" /> {submitError || sessionError}
          </p>
        )}

        <form onSubmit={onSubmit} noValidate className="mt-6 space-y-4">
          <div>
            <label htmlFor="email" className="mb-1.5 block text-sm font-medium text-slate-200">Email address</label>
            <div className="relative">
              <Mail className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-brand-sky" aria-hidden="true" />
              <input
                id="email" name="email" type="email" autoComplete="email" inputMode="email"
                placeholder="name@company.com"
                value={values.email} onChange={set("email")} onBlur={blur("email")}
                aria-invalid={Boolean(show("email"))} aria-describedby={show("email") ? "email-error" : undefined}
                className={`${FIELD} pl-10 ${show("email") ? "!border-bad" : ""}`}
              />
            </div>
            {show("email") && <p id="email-error" role="alert" className="mt-1.5 text-xs text-red-300">{errors.email}</p>}
          </div>

          <div>
            <label htmlFor="password" className="mb-1.5 block text-sm font-medium text-slate-200">Password</label>
            <div className="relative">
              <Lock className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-brand-sky" aria-hidden="true" />
              <input
                id="password" name="password" type={showPassword ? "text" : "password"} autoComplete="current-password"
                placeholder="Enter your password"
                value={values.password} onChange={set("password")} onBlur={blur("password")}
                aria-invalid={Boolean(show("password"))} aria-describedby={show("password") ? "password-error" : undefined}
                className={`${FIELD} pl-10 pr-11 ${show("password") ? "!border-bad" : ""}`}
              />
              <button
                type="button" onClick={() => setShowPassword((s) => !s)}
                aria-label={showPassword ? "Hide password" : "Show password"} aria-pressed={showPassword}
                className="absolute right-1.5 top-1/2 flex h-7 w-8 -translate-y-1/2 items-center justify-center rounded-md text-slate-300 hover:text-brand-cyan"
              >
                {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
            {show("password") && <p id="password-error" role="alert" className="mt-1.5 text-xs text-red-300">{errors.password}</p>}
          </div>

          <div className="flex items-center justify-between gap-3">
            <label className="flex cursor-pointer items-center gap-2 text-sm text-slate-200">
              <input
                type="checkbox" checked={remember} onChange={(e) => setRemember(e.target.checked)}
                className="h-4 w-4 cursor-pointer rounded border-sky-400/40 bg-navy-900 accent-brand-sky"
              />
              Remember me
            </label>
            <Link to="/forgot-password" className="link-accent">Forgot password?</Link>
          </div>

          <button type="submit" disabled={loading} className={`${BTN_PRIMARY} h-11 w-full`}>
            {loading ? <><Loader2 className="h-4 w-4 animate-spin" /> Signing in…</> : "Sign In"}
          </button>
        </form>

        <p className="mt-6 border-t border-sky-400/20 pt-5 text-center text-sm text-slate-300">
          New to RUNWAY X? <Link to="/register" className="link-accent">Create Company Account</Link>
        </p>
      </section>

      <p className="mt-5 flex items-center justify-center gap-2 text-xs text-slate-400">
        <ShieldCheck className="h-4 w-4 text-brand-sky" aria-hidden="true" /> Authorized users only.
      </p>
    </AuthShell>
  );
}
