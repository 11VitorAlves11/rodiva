import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";

import { auth } from "./api";
import { ApiError } from "./api/client";
import type { Me } from "./api/types";

type Session = {
  me: Me | null;
  loading: boolean;
  /** Set only when the session could not be checked — never when there is none. */
  error: Error | null;
  setMe: (me: Me | null) => void;
  refresh: () => Promise<void>;
  signOut: () => Promise<void>;
};

const SessionContext = createContext<Session | null>(null);

export function SessionProvider({ children }: { children: ReactNode }) {
  const [me, setMe] = useState<Me | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const refresh = useCallback(async () => {
    try {
      setMe(await auth.me());
      setError(null);
    } catch (cause) {
      // 401 is the normal "not signed in yet" answer, not a failure to report.
      if (cause instanceof ApiError && cause.isUnauthorized) {
        setMe(null);
        setError(null);
        return;
      }
      setError(cause instanceof Error ? cause : new Error(String(cause)));
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      await refresh();
      if (!cancelled) setLoading(false);
    })();
    return () => {
      cancelled = true;
    };
  }, [refresh]);

  const signOut = useCallback(async () => {
    await auth.logout();
    setMe(null);
  }, []);

  const value = useMemo<Session>(
    () => ({ me, loading, error, setMe, refresh, signOut }),
    [me, loading, error, refresh, signOut],
  );

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

export function useSession(): Session {
  const session = useContext(SessionContext);
  if (!session) throw new Error("useSession must be used inside a SessionProvider");
  return session;
}
