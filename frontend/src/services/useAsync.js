import { useEffect, useState } from "react";

/** Tiny data-loading hook: const { data, loading, error } = useAsync(getKpis) */
export function useAsync(fn) {
  const [state, setState] = useState({ data: null, loading: true, error: null });
  useEffect(() => {
    let alive = true;
    fn()
      .then((data) => alive && setState({ data, loading: false, error: null }))
      .catch((error) => alive && setState({ data: null, loading: false, error }));
    return () => { alive = false; };
  }, [fn]);
  return state;
}
