import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { auth } from "../../lib/api";
import type { AuthSession, Membership } from "../../lib/api/types";
import { useTheme } from "../../lib/theme";
import type { Theme } from "../../lib/theme";
import { useSession } from "../../lib/session";
import { useConfirm } from "../../components/ui/confirm-context";

const panel = "space-y-4 rounded-xl border border-line bg-raised p-5 shadow-sm";
const input = "mt-1 w-full rounded-md border border-line px-3 py-2 bg-raised";
const button = "rounded-lg bg-copper px-4 py-2 text-sm font-semibold text-white disabled:opacity-60";

export function AccountSettings() {
  const { t, i18n } = useTranslation();
  const confirm = useConfirm();
  const { me, setMe } = useSession();
  const { theme, setTheme } = useTheme();
  const [name, setName] = useState(me?.user.name ?? "");
  const [locale, setLocale] = useState(me?.user.locale ?? "pt-PT");
  const [timezone, setTimezone] = useState(me?.user.timezone ?? "Europe/Lisbon");
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [sessions, setSessions] = useState<AuthSession[] | null>(null);
  const [households, setHouseholds] = useState<Membership[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [reload, setReload] = useState(0);

  useEffect(() => {
    let active = true;
    void Promise.all([auth.sessions(), auth.households()]).then(([rows, memberships]) => {
      if (active) { setSessions(rows); setHouseholds(memberships); }
    }).catch(() => { if (active) setError(t("common.error")); });
    return () => { active = false; };
  }, [reload, t]);

  async function run(action: () => Promise<void>) {
    setBusy(true); setError(null); setSuccess(null);
    try { await action(); }
    catch { setError(t("common.error")); }
    finally { setBusy(false); }
  }

  function saveProfile(event: FormEvent) {
    event.preventDefault();
    void run(async () => {
      const user = await auth.profile({ name: name.trim() || null, locale, timezone });
      if (me) setMe({ ...me, user });
      await i18n.changeLanguage(user.locale);
      setSuccess(t("account.saved"));
    });
  }

  function changePassword(event: FormEvent) {
    event.preventDefault();
    if (newPassword !== confirmPassword) { setError(t("account.passwordMismatch")); return; }
    void run(async () => {
      try { await auth.changePassword({ current_password: currentPassword, new_password: newPassword }); }
      catch { setError(t("account.passwordError")); return; }
      setCurrentPassword(""); setNewPassword(""); setConfirmPassword("");
      setReload((value) => value + 1);
      setSuccess(t("account.passwordChanged"));
    });
  }

  return (
    <div className="space-y-6">
      {error && <div role="alert" className="rounded-lg bg-danger-soft p-3 text-sm text-danger">{error}<button className="ml-3 underline" onClick={() => { setError(null); setReload((value) => value + 1); }}>{t("common.retry")}</button></div>}
      {success && <p role="status" className="rounded-lg bg-success-soft p-3 text-sm text-success">{success}</p>}
      {households.length > 1 && <section className={panel}>
        <label className="block text-sm font-semibold">{t("account.activeHousehold")}
          <select disabled={busy} className={input} value={me?.membership.household_id ?? ""} onChange={(event) => {
            const id = event.target.value;
            void run(async () => { await auth.activateHousehold(id); window.location.assign("/"); });
          }}>{households.map((household) => <option key={household.household_id} value={household.household_id}>{household.household_name}</option>)}</select>
        </label>
      </section>}
      <form className={panel} onSubmit={saveProfile}>
        <h2 className="font-semibold">{t("settings.preferences")}</h2>
        <label className="block text-sm">{t("appearance.theme")}<select className={input} value={theme} onChange={(event) => setTheme(event.target.value as Theme)}>{(["system", "light", "dark"] as const).map((value) => <option key={value} value={value}>{t(`appearance.${value}`)}</option>)}</select></label>
        <label className="block text-sm">{t("account.name")}<input maxLength={200} className={input} value={name} onChange={(event) => setName(event.target.value)} autoComplete="name" /></label>
        <label className="block text-sm">{t("settings.language")}<select className={input} value={locale} onChange={(event) => setLocale(event.target.value)}><option value="pt-PT">Português</option><option value="en">English</option><option value="fr">Français</option><option value="es">Español</option></select></label>
        <label className="block text-sm">{t("account.timezone")}<input required maxLength={50} className={input} value={timezone} onChange={(event) => setTimezone(event.target.value)} list="timezones" /><datalist id="timezones">{["Europe/Lisbon", "Atlantic/Azores", "Europe/London", "Europe/Paris", "America/New_York", "UTC"].map((zone) => <option key={zone} value={zone} />)}</datalist></label>
        <button disabled={busy} className={button}>{t("garage.save")}</button>
      </form>
      <form className={panel} onSubmit={changePassword}>
        <h2 className="font-semibold">{t("account.changePassword")}</h2>
        <label className="block text-sm">{t("account.currentPassword")}<input required type="password" autoComplete="current-password" className={input} value={currentPassword} onChange={(event) => setCurrentPassword(event.target.value)} /></label>
        <label className="block text-sm">{t("account.newPassword")}<input required minLength={10} maxLength={72} type="password" autoComplete="new-password" className={input} value={newPassword} onChange={(event) => setNewPassword(event.target.value)} /></label>
        <label className="block text-sm">{t("account.confirmPassword")}<input required minLength={10} maxLength={72} type="password" autoComplete="new-password" className={input} value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)} /></label>
        <p className="text-sm text-ink-muted">{t("account.passwordHint")}</p>
        <button disabled={busy} className={button}>{t("account.changePassword")}</button>
      </form>
      <section className={panel}>
        <h2 className="font-semibold">{t("account.sessions")}</h2>
        {!sessions ? <p>{t("common.loading")}</p> : <ul className="divide-y divide-graphite/10 dark:divide-white/10">{sessions.map((session) => <li key={session.id} className="flex flex-wrap items-center justify-between gap-3 py-3">
          <div className="min-w-0 flex-1"><p className="break-words text-sm">{session.user_agent || t("account.unknownDevice")}</p><p className="text-xs text-ink-muted">{new Intl.DateTimeFormat(i18n.language, { dateStyle: "medium", timeStyle: "short", timeZone: me?.user.timezone }).format(new Date(session.created_at))}{session.current ? ` · ${t("account.currentSession")}` : ""}</p></div>
          <button disabled={busy} className="text-sm font-semibold text-danger disabled:opacity-60" onClick={() => void run(async () => { await auth.revokeSession(session.id); if (session.current) setMe(null); else setSessions((rows) => rows?.filter((row) => row.id !== session.id) ?? null); })}>{t("account.endSession")}</button>
        </li>)}</ul>}
        <button disabled={busy} className="rounded-lg border border-copper/30 px-4 py-2 text-sm font-semibold text-copper disabled:opacity-60" onClick={async () => {
          if (await confirm(t("account.endAllConfirm"))) void run(async () => { await auth.logoutAll(); setMe(null); });
        }}>{t("account.endAll")}</button>
      </section>
    </div>
  );
}
