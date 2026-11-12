import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import * as authApi from "../../services/authApi.js";

/**
 * Holds who is signed in. On first load (including after a browser refresh) it asks the backend
 * "who am I?" — the answer comes from the HttpOnly session cookie, so no tokens are stored in the browser.
 *
 * status: "loading" (checking) | "authenticated" | "unauthenticated"
 */
const SIGNED_OUT = { status: "unauthenticated", user: null, csrfToken: null, error: "" };
const AuthContext = createContext(null);

const signedIn = (s) => ({ status: "authenticated", user: s.user, csrfToken: s.csrfToken, error: "" });

export function AuthProvider({ children }) {
  const [state, setState] = useState({ status: "loading", user: null, csrfToken: null, error: "" });

  useEffect(() => {
    let alive = true;
    authApi.getSession()
      .then((s) => alive && setState(s ? signedIn(s) : SIGNED_OUT))
      .catch((err) => alive && setState({ ...SIGNED_OUT, error: err.message }));
    return () => { alive = false; };
  }, []);

  const signIn = useCallback(async (credentials) => {
    setState(signedIn(await authApi.login(credentials)));
  }, []);

  const signOut = useCallback(async () => {
    try {
      await authApi.logout(state.csrfToken);
    } catch (err) {
      // The CSRF token may be stale. Fetch a fresh one once; if we are already signed out, that's fine.
      const fresh = await authApi.getSession().catch(() => { throw err; });
      if (fresh) await authApi.logout(fresh.csrfToken);
    }
    setState(SIGNED_OUT);
  }, [state.csrfToken]);

  const value = useMemo(() => ({ ...state, signIn, signOut }), [state, signIn, signOut]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>.");
  return ctx;
}
