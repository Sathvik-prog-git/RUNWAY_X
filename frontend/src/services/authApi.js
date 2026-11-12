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
