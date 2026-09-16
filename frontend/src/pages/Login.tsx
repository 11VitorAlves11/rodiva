import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Link, Navigate, useLocation } from "react-router-dom";

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

  const [options, setOptions] = useState({ registration: true, password_recovery: false });
  useEffect(() => { void auth.options().then(setOptions).catch(() => {}); }, []);

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
    <div className="flex min-h-screen items-center justify-center bg-cream px-4">
      <form onSubmit={handleSubmit} className="w-full max-w-sm space-y-4 rounded-xl border border-graphite/10 bg-white p-6 shadow-sm">
        <div className="mb-2 flex items-center gap-2">
          <Logo size={32} />
          <span className="text-lg font-bold text-graphite">Rodiva</span>
        </div>
        <h1 className="text-xl font-semibold text-graphite">
          {mode === "login" ? t("login.title") : t("register.title")}
        </h1>

        {mode === "register" && (
          <>
            <Field label={t("register.householdName")} value={householdName} onChange={setHouseholdName} required />
            <Field label={t("register.name")} value={name} onChange={setName} />
          </>
        )}
        <Field label={t("login.email")} type="email" value={email} onChange={setEmail} required />
        <Field label={t("login.password")} type="password" value={password} onChange={setPassword} required />

        {error && <p className="text-sm text-red-700">{error}</p>}

        <button
          type="submit"
          disabled={submitting}
          className="w-full rounded-md bg-copper px-4 py-2 text-sm font-medium text-white hover:bg-copper-dark disabled:opacity-60"
        >
          {mode === "login" ? t("login.submit") : t("register.submit")}
        </button>

        {options.password_recovery && <Link to="/forgot-password" className="block text-center text-sm font-medium text-copper">{t("recovery.forgot")}</Link>}
        <p className="text-center text-sm text-graphite/50">
          {mode === "login" && options.registration ? (
            <>
              {t("login.noAccount")}{" "}
              <button type="button" className="font-medium text-copper" onClick={() => setMode("register")}>
                {t("login.register")}
              </button>
            </>
          ) : (
            <button type="button" className="font-medium text-copper" onClick={() => setMode("login")}>
              {t("login.title")}
            </button>
          )}
        </p>
      </form>
    </div>
  );
}

function Field({
  label,
  value,
  onChange,
  type = "text",
  required,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  type?: string;
  required?: boolean;
}) {
  return (
    <label className="block text-sm">
      <span className="mb-1 block font-medium text-graphite/70">{label}</span>
      <input
        type={type}
        value={value}
        required={required}
        onChange={(event) => onChange(event.target.value)}
        className="w-full rounded-md border border-graphite/15 px-3 py-2 focus-visible:border-copper"
      />
    </label>
  );
}
