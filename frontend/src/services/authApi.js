/**
 * Auth API client for the FastAPI backend (/api/auth/*).
 *
 * The session lives in an HttpOnly cookie that JavaScript cannot read, so nothing secret is kept in
 * localStorage. `credentials: "include"` makes the browser send that cookie. The CSRF token returned
 * by login() / getSession() is held in memory only and sent back on logout.
 */
const NETWORK_ERROR = "Can't reach the server. Make sure the backend is running, then try again.";

async function call(path, options = {}) {
  try {
    return await fetch(`/api/auth${path}`, { credentials: "include", ...options });
  } catch {
    throw new Error(NETWORK_ERROR);
  }
}

async function errorMessage(res) {
  let detail = "";
  try {
    const body = await res.json();
    if (typeof body.detail === "string") detail = body.detail;
  } catch { /* response had no JSON body */ }
  if (detail) return detail;
  if (res.status === 422) return "Please check your email and password and try again.";
  if (res.status === 403) return "Your request was blocked for security reasons. Refresh the page and try again.";
  if (res.status >= 500) return "The server had a problem. Please try again in a moment.";
  return `Request failed (${res.status}).`;
}

/** @returns {Promise<{user: {id:number,email:string,role:string}, csrfToken: string}>} */
export async function login({ email, password, remember }) {
  const res = await call("/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password, remember: Boolean(remember) }),
  });
  if (!res.ok) throw new Error(await errorMessage(res));
  return res.json();
}

/** Current session, or null when not signed in. Throws only if the server can't be reached or errors. */
export async function getSession() {
  const res = await call("/me");
  if (res.status === 401) return null;
  if (!res.ok) throw new Error(await errorMessage(res));
  return res.json();
}

export async function logout(csrfToken) {
  const res = await call("/logout", { method: "POST", headers: { "X-CSRF-Token": csrfToken || "" } });
  if (!res.ok) throw new Error(await errorMessage(res));
}

const REGISTER_FIELDS = {
  full_name: "fullName", email: "email", password: "password", confirm_password: "confirmPassword",
  company_name: "companyName", phone: "phone", gstin: "gstin",
};

/** Error carrying the server's per-field messages (from a 422) so the form can show them next to the fields. */
export class RegistrationError extends Error {
  constructor(message, fieldErrors = {}) {
    super(message);
    this.fieldErrors = fieldErrors;
  }
}

/**
 * Create a company + its owner account. The backend decides the role (always OWNER) and the company;
 * this function sends only the form fields. On success the user is already signed in (cookie set).
 * @returns {Promise<{user: {id:number,email:string,role:string}, csrfToken: string}>}
 */
export async function register(form) {
  const res = await call("/register", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      full_name: form.fullName,
      email: form.email,
      password: form.password,
      confirm_password: form.confirmPassword,
      company_name: form.companyName,
      phone: form.phone,
      gstin: form.gstin || null,
    }),
  });
  if (res.ok) return res.json();
  if (res.status === 422) {
    const fieldErrors = {};
    try {
      const body = await res.json();
      for (const item of Array.isArray(body.detail) ? body.detail : []) {
        const key = REGISTER_FIELDS[item.loc?.[item.loc.length - 1]];
        if (key && !fieldErrors[key]) fieldErrors[key] = String(item.msg || "").replace(/^Value error, /, "");
      }
    } catch { /* no JSON body */ }
    throw new RegistrationError("Please fix the highlighted fields and try again.", fieldErrors);
  }
  if (res.status === 429) throw new RegistrationError("Too many attempts. Please wait a while and try again.");
  throw new RegistrationError(await errorMessage(res));
}
