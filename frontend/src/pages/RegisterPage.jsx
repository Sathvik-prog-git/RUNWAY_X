import { useRef, useState } from "react";
import { Link, Navigate } from "react-router-dom";
import { AlertCircle, Building2, CheckCircle2, Eye, EyeOff, FileText, Loader2, Lock, Mail, Phone, ShieldCheck, User } from "lucide-react";
import AuthShell from "../components/auth/AuthShell.jsx";
import PasswordStrengthMeter from "../components/auth/PasswordStrengthMeter.jsx";
import { AuthLoading } from "../components/auth/ProtectedRoute.jsx";
import { useAuth } from "../components/auth/AuthContext.jsx";
import { BTN_PRIMARY, FIELD } from "../components/transactions/fieldStyles.js";
import { normalizeGstin, normalizeIndianMobile, validateRegistration } from "../utils/registerValidation.js";

const EMPTY = { fullName: "", email: "", password: "", confirmPassword: "", companyName: "", phone: "", gstin: "" };

/** One labelled input with an icon, an inline error and optional hint. */
function Field({ id, label, icon: Icon, error, hint, optional, children }) {
  return (
    <div>
      <label htmlFor={id} className="mb-1.5 flex items-baseline justify-between text-sm font-medium text-slate-200">
        <span>{label}</span>
        {optional && <span className="text-xs font-normal text-slate-400">Optional</span>}
      </label>
      <div className="relative">
        <Icon className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-brand-sky" aria-hidden="true" />
        {children}
      </div>
      {error ? (
        <p id={`${id}-error`} role="alert" className="mt-1.5 text-xs text-red-300">{error}</p>
      ) : hint ? (
        <p className="mt-1.5 text-xs text-slate-400">{hint}</p>
      ) : null}
    </div>
  );
}

export default function RegisterPage() {
  const { status, register, user } = useAuth();
  const [values, setValues] = useState(EMPTY);
  const [touched, setTouched] = useState({});
  const [serverErrors, setServerErrors] = useState({});
  const [submitError, setSubmitError] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [done, setDone] = useState(false);
  const submitted = useRef(false); // true once we started registering: stops the "already signed in" redirect below

  // Signed-in visitors have no business here — unless they just created this account (then we show the success panel).
  if (status === "loading") return <AuthLoading />;
  if (status === "authenticated" && !submitted.current) return <Navigate to="/" replace />;

  const errors = validateRegistration(values);
  const show = (f) => (touched[f] && errors[f]) || serverErrors[f] || "";
  const invalid = (f) => (show(f) ? "!border-bad" : "");
  const aria = (f) => ({ "aria-invalid": Boolean(show(f)), "aria-describedby": show(f) ? `${f}-error` : undefined });

  const set = (field, transform = (x) => x) => (e) => {
    setValues((v) => ({ ...v, [field]: transform(e.target.value) }));
    setServerErrors((s) => ({ ...s, [field]: undefined })); // the user is fixing it: drop the server's old message
    setSubmitError("");
  };
  const blur = (field) => () => setTouched((t) => ({ ...t, [field]: true }));

  async function onSubmit(e) {
    e.preventDefault();
    setTouched(Object.fromEntries(Object.keys(EMPTY).map((k) => [k, true])));
    setSubmitError("");
    if (Object.keys(errors).length) return;
    setLoading(true);
    submitted.current = true;
    try {
      await register({
        fullName: values.fullName.trim(),
        email: values.email.trim(),
        password: values.password,
        confirmPassword: values.confirmPassword,
        companyName: values.companyName.trim(),
        phone: values.phone,
        gstin: normalizeGstin(values.gstin),
      });
      setDone(true);
    } catch (err) {
      submitted.current = false;
      setServerErrors(err.fieldErrors || {});
      setSubmitError(err.message || "We couldn't create your account. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  if (done) {
    return (
      <AuthShell>
        <section className="panel p-6 text-center sm:p-8" aria-labelledby="done-title" role="status">
          <CheckCircle2 className="mx-auto h-12 w-12 text-good" aria-hidden="true" />
          <h1 id="done-title" className="mt-4 text-2xl font-semibold tracking-tight">Your company account is ready</h1>
          <p className="mt-2 text-sm text-slate-200">
            Welcome{user?.email ? `, ${user.email}` : ""}. You are signed in as the owner of <strong>{values.companyName.trim()}</strong>.
          </p>
          <Link to="/" replace className={`${BTN_PRIMARY} mt-6 h-11 w-full`}>Go to dashboard</Link>
        </section>
      </AuthShell>
    );
  }

  return (
    <AuthShell>
      <section className="panel p-6 sm:p-8" aria-labelledby="register-title">
        <h1 id="register-title" className="text-3xl font-semibold tracking-tight">Create Company Account</h1>
        <p className="mt-1.5 text-sm text-slate-200">Set up RUNWAY X for your business. You will be the account owner.</p>

        {submitError && (
          <p role="alert" className="mt-5 flex items-start gap-2 rounded-lg border border-bad/40 bg-bad/10 p-3 text-sm text-red-200">
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" /> {submitError}
          </p>
        )}

        <form onSubmit={onSubmit} noValidate className="mt-6 space-y-4">
          <Field id="fullName" label="Full name" icon={User} error={show("fullName")}>
            <input id="fullName" name="fullName" type="text" autoComplete="name" placeholder="Your full name"
              value={values.fullName} onChange={set("fullName")} onBlur={blur("fullName")} {...aria("fullName")}
              className={`${FIELD} pl-10 ${invalid("fullName")}`} />
          </Field>

          <Field id="email" label="Work email" icon={Mail} error={show("email")}>
            <input id="email" name="email" type="email" autoComplete="email" inputMode="email" placeholder="name@company.com"
              value={values.email} onChange={set("email")} onBlur={blur("email")} {...aria("email")}
              className={`${FIELD} pl-10 ${invalid("email")}`} />
          </Field>

          <div>
            <Field id="password" label="Password" icon={Lock} error={show("password")} hint="At least 12 characters. A short phrase works well.">
              <input id="password" name="password" type={showPassword ? "text" : "password"} autoComplete="new-password"
                placeholder="Create a password" value={values.password} onChange={set("password")} onBlur={blur("password")}
                {...aria("password")} className={`${FIELD} pl-10 pr-11 ${invalid("password")}`} />
              <button type="button" onClick={() => setShowPassword((s) => !s)}
                aria-label={showPassword ? "Hide passwords" : "Show passwords"} aria-pressed={showPassword}
                className="absolute right-1.5 top-1/2 flex h-7 w-8 -translate-y-1/2 items-center justify-center rounded-md text-slate-300 hover:text-brand-cyan">
                {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </Field>
            <PasswordStrengthMeter password={values.password} email={values.email} fullName={values.fullName} />
          </div>

          <Field id="confirmPassword" label="Confirm password" icon={Lock} error={show("confirmPassword")}>
            <input id="confirmPassword" name="confirmPassword" type={showPassword ? "text" : "password"} autoComplete="new-password"
              placeholder="Re-enter your password" value={values.confirmPassword} onChange={set("confirmPassword")}
              onBlur={blur("confirmPassword")} {...aria("confirmPassword")} className={`${FIELD} pl-10 ${invalid("confirmPassword")}`} />
          </Field>

          <Field id="companyName" label="Company name" icon={Building2} error={show("companyName")}>
            <input id="companyName" name="companyName" type="text" autoComplete="organization" placeholder="Your registered business name"
              value={values.companyName} onChange={set("companyName")} onBlur={blur("companyName")} {...aria("companyName")}
              className={`${FIELD} pl-10 ${invalid("companyName")}`} />
          </Field>

          <Field id="phone" label="Mobile number" icon={Phone} error={show("phone")}
            hint={normalizeIndianMobile(values.phone) ? `Will be saved as ${normalizeIndianMobile(values.phone)}` : "Indian mobile, e.g. 98765 43210"}>
            <input id="phone" name="phone" type="tel" autoComplete="tel" inputMode="tel" placeholder="98765 43210"
              value={values.phone} onChange={set("phone")} onBlur={blur("phone")} {...aria("phone")}
              className={`${FIELD} pl-10 ${invalid("phone")}`} />
          </Field>

          <Field id="gstin" label="GSTIN" icon={FileText} optional error={show("gstin")} hint="15 characters, e.g. 22AAAAA0000A1Z5">
            <input id="gstin" name="gstin" type="text" autoComplete="off" maxLength={15} placeholder="Leave blank if you don't have one"
              value={values.gstin} onChange={set("gstin", (x) => x.toUpperCase())} onBlur={blur("gstin")} {...aria("gstin")}
              className={`${FIELD} pl-10 uppercase ${invalid("gstin")}`} />
          </Field>

          <button type="submit" disabled={loading} className={`${BTN_PRIMARY} h-11 w-full`}>
            {loading ? <><Loader2 className="h-4 w-4 animate-spin" /> Creating account…</> : "Create Company Account"}
          </button>
        </form>

        <p className="mt-6 border-t border-sky-400/20 pt-5 text-center text-sm text-slate-300">
          Already have an account? <Link to="/login" className="link-accent">Sign in</Link>
        </p>
      </section>

      <p className="mt-5 flex items-center justify-center gap-2 text-xs text-slate-400">
        <ShieldCheck className="h-4 w-4 text-brand-sky" aria-hidden="true" /> Your password is stored only as a secure hash.
      </p>
    </AuthShell>
  );
}
