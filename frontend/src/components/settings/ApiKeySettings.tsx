import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { apiKeys, vehicles } from "../../lib/api";
import type { ApiKey, Vehicle } from "../../lib/api/types";
import { useSession } from "../../lib/session";

export function ApiKeySettings() {
  const { t, i18n } = useTranslation();
  const { me } = useSession();
  const [keys, setKeys] = useState<ApiKey[] | null>(null);
  const [list, setList] = useState<Vehicle[]>([]);
  const [name, setName] = useState("");
  const [scope, setScope] = useState<"read" | "write">("read");
  const [days, setDays] = useState(90);
  const [selected, setSelected] = useState<string[]>([]);
  const [token, setToken] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);
  const input = "mt-1 w-full rounded-lg border border-graphite/15 px-3 py-2 dark:border-white/15 dark:bg-surface-dark";
  useEffect(() => {
    let active = true;
    void Promise.all([apiKeys.list(), vehicles.list()]).then(([rows, options]) => { if (active) { setKeys(rows); setList(options); } }).catch(() => { if (active) setError(t("common.error")); });
    return () => { active = false; };
  }, [attempt, t]);
  async function create(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError(null);
    try {
      const result = await apiKeys.create({ name, scope, vehicle_ids: selected, expires_in_days: days });
      setToken(result.token); setName(""); setAttempt((value) => value + 1);
    } catch { setError(t("common.error")); }
    finally { setBusy(false); }
  }
  return <section className="space-y-4 rounded-xl border border-graphite/10 bg-white p-5 shadow-sm dark:border-white/10 dark:bg-surface-dark-raised">
    <h2 className="font-semibold">{t("apiKeys.title")}</h2>
    <p className="text-sm text-graphite/60 dark:text-cream/60">{t("apiKeys.description")}</p>
    {error && <p role="alert" className="text-sm text-red-700">{error}<button className="ml-2 underline" onClick={() => { setError(null); setAttempt((value) => value + 1); }}>{t("common.retry")}</button></p>}
    {token && <div className="space-y-2 rounded-lg border border-copper/30 p-3"><p className="text-sm font-medium">{t("apiKeys.once")}</p><input readOnly aria-label={t("apiKeys.token")} value={token} onFocus={(event) => event.target.select()} className={`${input} font-mono text-xs`} /><button onClick={() => setToken(null)} className="text-sm font-semibold text-copper">{t("apiKeys.saved")}</button></div>}
    <form onSubmit={create}><fieldset disabled={busy || token !== null} className="grid gap-3 sm:grid-cols-2">
      <label className="text-sm">{t("apiKeys.name")}<input required maxLength={100} value={name} onChange={(event) => setName(event.target.value)} className={input} /></label>
      <label className="text-sm">{t("apiKeys.days")}<input type="number" required min="1" max="365" value={days} onChange={(event) => setDays(Number(event.target.value))} className={input} /></label>
      <label className="text-sm sm:col-span-2">{t("apiKeys.permissions")}<select value={scope} onChange={(event) => setScope(event.target.value as "read" | "write")} className={input}><option value="read">{t("apiKeys.read")}</option>{me?.membership.role !== "reader" && <option value="write">{t("apiKeys.write")}</option>}</select></label>
      <div className="sm:col-span-2"><p className="mb-2 text-sm">{t("apiKeys.vehicles")}</p><div className="flex flex-wrap gap-3">{list.map((vehicle) => <label key={vehicle.id} className="flex items-center gap-2 text-sm"><input type="checkbox" checked={selected.includes(vehicle.id)} onChange={(event) => setSelected((current) => event.target.checked ? [...current, vehicle.id] : current.filter((id) => id !== vehicle.id))} />{vehicle.name}</label>)}</div><p className="mt-2 text-xs text-graphite/60 dark:text-cream/60">{t("apiKeys.vehicleHint")}</p></div>
      <button className="rounded-lg bg-copper px-4 py-2 font-semibold text-white disabled:opacity-60 sm:col-span-2">{t("apiKeys.create")}</button>
    </fieldset></form>
    {!keys ? <p>{t("common.loading")}</p> : <ul className="divide-y divide-graphite/10 dark:divide-white/10">{keys.map((key) => <li key={key.id} className="flex flex-wrap items-center justify-between gap-3 py-3"><div><p className="font-medium">{key.name}</p><p className="text-xs">{t(`apiKeys.${key.scope}`)} · {t("apiKeys.expires")} {new Intl.DateTimeFormat(i18n.language).format(new Date(key.expires_at))}{key.revoked_at ? ` · ${t("apiKeys.revoked")}` : ""}</p></div>{!key.revoked_at && <button disabled={busy} className="text-sm font-semibold text-red-700 disabled:opacity-60" onClick={() => {
      if (!window.confirm(t("apiKeys.confirmRevoke"))) return;
      setBusy(true); setError(null);
      void apiKeys.revoke(key.id).then(() => setAttempt((value) => value + 1)).catch(() => setError(t("common.error"))).finally(() => setBusy(false));
    }}>{t("settings.revoke")}</button>}</li>)}</ul>}
  </section>;
}
