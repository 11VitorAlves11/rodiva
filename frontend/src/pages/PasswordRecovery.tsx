import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { auth } from "../lib/api";
import { ApiError } from "../lib/api/client";
import { useSession } from "../lib/session";

export function PasswordRecovery({ reset = false }: { reset?: boolean }) {
  const { t } = useTranslation();
  const { setMe } = useSession();
  const [token] = useState(() => new URLSearchParams(window.location.hash.slice(1)).get("token") ?? "");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    if (reset && window.location.hash) window.history.replaceState(window.history.state, "", window.location.pathname);
  }, [reset]);

  async function submit(event: FormEvent) {
    event.preventDefault(); setError(null);
    if (reset && password !== confirmation) { setError(t("account.passwordMismatch")); return; }
    setBusy(true);
    try {
      if (reset) { await auth.resetPassword(token, password); setMe(null); }
      else await auth.forgotPassword(email);
      setDone(true);
    } catch (cause) {
      setError(t(cause instanceof ApiError && cause.status === 429 ? "recovery.tooMany" : reset ? "recovery.invalid" : "recovery.unavailable"));
    } finally { setBusy(false); }
  }

  const input = "mt-1 w-full rounded-lg border border-line-strong px-3 py-2 bg-raised";
  return <div className="flex min-h-screen items-center justify-center bg-surface px-4">
    <form onSubmit={submit} className="w-full max-w-sm space-y-4 rounded-xl border border-line bg-raised p-6 shadow-sm">
      <h1 className="text-xl font-semibold">{t(reset ? "recovery.reset" : "recovery.forgot")}</h1>
      {done ? <p role="status" className="text-sm">{t(reset ? "recovery.resetDone" : "recovery.sent")}</p> : <>
        {reset ? <>
          <label className="block text-sm">{t("account.newPassword")}<input required type="password" autoComplete="new-password" minLength={10} maxLength={72} className={input} value={password} onChange={(event) => setPassword(event.target.value)} /></label>
          <label className="block text-sm">{t("account.confirmPassword")}<input required type="password" autoComplete="new-password" minLength={10} maxLength={72} className={input} value={confirmation} onChange={(event) => setConfirmation(event.target.value)} /></label>
        </> : <label className="block text-sm">{t("login.email")}<input required type="email" autoComplete="email" className={input} value={email} onChange={(event) => setEmail(event.target.value)} /></label>}
        {error && <p role="alert" className="text-sm text-danger">{error}</p>}
        {reset && !token && <p role="alert" className="text-sm text-danger">{t("recovery.invalid")}</p>}
        <button disabled={busy || (reset && !token)} className="w-full rounded-lg bg-copper px-4 py-2 font-semibold text-white disabled:opacity-60">{t(reset ? "recovery.reset" : "recovery.send")}</button>
      </>}
      <Link to="/login" className="block text-center text-sm font-medium text-copper">{t("login.title")}</Link>
    </form>
  </div>;
}
