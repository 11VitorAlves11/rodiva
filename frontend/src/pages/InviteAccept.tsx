import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Navigate, useParams } from "react-router-dom";

import { Logo } from "../components/ui/Logo";
import { auth } from "../lib/api";
import { ApiError } from "../lib/api/client";
import type { InvitePreview, Me } from "../lib/api/types";
import { useSession } from "../lib/session";

export function InviteAccept() {
  const { t } = useTranslation();
  const { token = "" } = useParams();
  const { me, loading: sessionLoading, setMe } = useSession();
  const [preview, setPreview] = useState<InvitePreview | null | "invalid">(null);
  const [accepting, setAccepting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [joined, setJoined] = useState(false);

  useEffect(() => {
    auth.previewInvite(token).then(setPreview).catch(() => setPreview("invalid"));
  }, [token]);

  if (joined) return <Navigate to="/" replace />;
  const ready = preview !== null && !sessionLoading;

  async function acceptAsCurrentUser() {
    setAccepting(true);
    setError(null);
    try {
      setMe(await auth.acceptInvite(token));
      setJoined(true);
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : t("common.error"));
    } finally {
      setAccepting(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-cream px-4">
      <div className="w-full max-w-sm space-y-4 rounded-xl border border-graphite/10 bg-raised p-6 shadow-sm">
        <div className="mb-2 flex items-center gap-2">
          <Logo size={32} />
          <span className="text-lg font-bold text-graphite">Rodiva</span>
        </div>

        {!ready && <p className="text-sm text-graphite/50">{t("common.loading")}</p>}
        {ready && preview === "invalid" && <p className="text-sm text-red-700">{t("invite.invalid")}</p>}

        {ready && preview && preview !== "invalid" && (
          <>
            <p className="text-sm text-graphite/70">
              {t("invite.description", { household: preview.household_name, role: t(`settings.roles.${preview.role}`) })}
            </p>
            {error && <p className="text-sm text-red-700">{error}</p>}
            {me ? (
              <button
                onClick={() => void acceptAsCurrentUser()}
                disabled={accepting}
                className="w-full rounded-md bg-copper px-4 py-2 text-sm font-medium text-white hover:bg-copper-dark disabled:opacity-60"
              >
                {t("invite.accept", { email: me.user.email })}
              </button>
            ) : (
              <InviteAuthForm
                token={token}
                onJoined={(result) => {
                  setMe(result);
                  setJoined(true);
                }}
              />
            )}
          </>
        )}
      </div>
    </div>
  );
}

function InviteAuthForm({ token, onJoined }: { token: string; onJoined: (me: Me) => void }) {
  const { t } = useTranslation();
  const [mode, setMode] = useState<"register" | "login">("register");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      if (mode === "register") {
        onJoined(await auth.register({ email, password, name: name || undefined, invite_token: token }));
      } else {
        await auth.login({ email, password });
        onJoined(await auth.acceptInvite(token));
      }
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : t("common.error"));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={submit} className="space-y-3">
      {mode === "register" && (
        <label className="block text-sm">
          <span className="mb-1 block font-medium text-graphite/70">{t("register.name")}</span>
          <input value={name} onChange={(event) => setName(event.target.value)} className="w-full rounded-md border border-graphite/15 px-3 py-2" />
        </label>
      )}
      <label className="block text-sm">
        <span className="mb-1 block font-medium text-graphite/70">{t("login.email")}</span>
        <input required type="email" value={email} onChange={(event) => setEmail(event.target.value)} className="w-full rounded-md border border-graphite/15 px-3 py-2" />
      </label>
      <label className="block text-sm">
        <span className="mb-1 block font-medium text-graphite/70">{t("login.password")}</span>
        <input required type="password" value={password} onChange={(event) => setPassword(event.target.value)} className="w-full rounded-md border border-graphite/15 px-3 py-2" />
      </label>
      {error && <p className="text-sm text-red-700">{error}</p>}
      <button type="submit" disabled={submitting} className="w-full rounded-md bg-copper px-4 py-2 text-sm font-medium text-white hover:bg-copper-dark disabled:opacity-60">
        {mode === "register" ? t("invite.joinAsNewAccount") : t("invite.joinWithExistingAccount")}
      </button>
      <button
        type="button"
        onClick={() => setMode((value) => (value === "register" ? "login" : "register"))}
        className="w-full text-center text-sm font-medium text-copper"
      >
        {mode === "register" ? t("invite.haveAccount") : t("invite.needAccount")}
      </button>
    </form>
  );
}
