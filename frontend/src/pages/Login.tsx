import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Link, Navigate, useLocation, useSearchParams } from "react-router-dom";

import { Button } from "../components/ui/Button";
import { Field, Input } from "../components/ui/Field";
import { Logo } from "../components/ui/Logo";
import { auth } from "../lib/api";
import { ApiError } from "../lib/api/client";
import { useSession } from "../lib/session";

export function Login() {
  const { t } = useTranslation();
  const location = useLocation();
  const { me, setMe } = useSession();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [householdName, setHouseholdName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const [options, setOptions] = useState({ registration: true, password_recovery: false, oidc: false });
  useEffect(() => { void auth.options().then(setOptions).catch(() => {}); }, []);

  // The OIDC callback cannot render anything itself, so it lands back here with
  // the reason in the query rather than echoing the provider's own message.
  const [searchParams] = useSearchParams();
  const oidcOutcome = searchParams.get("oidc");

  if (me) {
    const from = (location.state as { from?: string } | null)?.from ?? "/";
    return <Navigate to={from} replace />;
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const result =
        mode === "login"
          ? await auth.login({ email, password })
          : await auth.register({ email, password, household_name: householdName, name });
      setMe(result);
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : t("common.error"));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-surface px-4">
      <form onSubmit={handleSubmit} className="w-full max-w-sm space-y-4 rounded-xl border border-line bg-raised p-6 shadow-sm">
        <div className="mb-2 flex items-center gap-2">
          <Logo size={32} />
          <span className="text-lg font-bold text-ink">Rodiva</span>
        </div>
        <h1 className="text-xl font-semibold text-ink">
          {mode === "login" ? t("login.title") : t("register.title")}
        </h1>

        {mode === "register" && (
          <>
            <Field label={t("register.householdName")} required>
              <Input value={householdName} required onChange={(event) => setHouseholdName(event.target.value)} />
            </Field>
            <Field label={t("register.name")}>
              <Input value={name} onChange={(event) => setName(event.target.value)} />
            </Field>
          </>
        )}
        <Field label={t("login.email")} required>
          <Input type="email" value={email} required autoComplete="email" onChange={(event) => setEmail(event.target.value)} />
        </Field>
        <Field label={t("login.password")} required>
          <Input
            type="password"
            value={password}
            required
            autoComplete={mode === "login" ? "current-password" : "new-password"}
            onChange={(event) => setPassword(event.target.value)}
          />
        </Field>

        {oidcOutcome && !error && (
          <p role="alert" className="text-sm text-danger">
            {oidcOutcome === "unknown" ? t("login.oidcUnknown") : t("login.oidcFailed")}
          </p>
        )}
        {error && <p className="text-sm text-danger">{error}</p>}

        <Button type="submit" disabled={submitting} className="w-full">
          {mode === "login" ? t("login.submit") : t("register.submit")}
        </Button>

        {options.oidc && (
          <>
            <div className="flex items-center gap-3 text-xs text-ink-subtle">
              <span className="h-px flex-1 bg-line" />
              {t("login.or")}
              <span className="h-px flex-1 bg-line" />
            </div>
            {/* A full page navigation, not fetch: the provider answers with a
                redirect the browser has to follow itself. */}
            <a
              href="/auth/oidc/start"
              className="block w-full rounded-lg border border-line px-4 py-2.5 text-center text-sm font-semibold text-ink hover:bg-sunken"
            >
              {t("login.withProvider")}
            </a>
          </>
        )}
        {options.password_recovery && <Link to="/forgot-password" className="block text-center text-sm font-medium text-brand">{t("recovery.forgot")}</Link>}
        <p className="text-center text-sm text-ink-subtle">
          {mode === "login" && options.registration ? (
            <>
              {t("login.noAccount")}{" "}
              <button type="button" className="font-medium text-brand" onClick={() => setMode("register")}>
                {t("login.register")}
              </button>
            </>
          ) : (
            <button type="button" className="font-medium text-brand" onClick={() => setMode("login")}>
              {t("login.title")}
            </button>
          )}
        </p>
      </form>
    </div>
  );
}
