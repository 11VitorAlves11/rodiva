import { useState } from "react";
import type { FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Navigate, useLocation } from "react-router-dom";

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
    <div className="flex min-h-screen items-center justify-center bg-slate-50 px-4">
      <form onSubmit={handleSubmit} className="w-full max-w-sm space-y-4 rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
        <h1 className="text-xl font-semibold text-slate-900">
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
          className="w-full rounded-md bg-blue-700 px-4 py-2 text-sm font-medium text-white hover:bg-blue-800 disabled:opacity-60"
        >
          {mode === "login" ? t("login.submit") : t("register.submit")}
        </button>

        <p className="text-center text-sm text-slate-500">
          {mode === "login" ? (
            <>
              {t("login.noAccount")}{" "}
              <button type="button" className="font-medium text-blue-700" onClick={() => setMode("register")}>
                {t("login.register")}
              </button>
            </>
          ) : (
            <button type="button" className="font-medium text-blue-700" onClick={() => setMode("login")}>
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
      <span className="mb-1 block font-medium text-slate-700">{label}</span>
      <input
        type={type}
        value={value}
        required={required}
        onChange={(event) => onChange(event.target.value)}
        className="w-full rounded-md border border-slate-300 px-3 py-2 focus-visible:border-blue-700"
      />
    </label>
  );
}
