import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { imports, vehicles } from "../lib/api";
import type { ImportKind, ImportPreview } from "../lib/api";
import type { Vehicle } from "../lib/api/types";
import { useSession } from "../lib/session";

const input = "mt-1 w-full rounded-lg border border-line px-3 py-2 bg-raised";
export function ImportRecords() {
  const { t, i18n } = useTranslation();
  const { me } = useSession();
  const [list, setList] = useState<Vehicle[]>([]);
  const [vehicleId, setVehicleId] = useState("");
  const [kind, setKind] = useState<ImportKind>("fuel");
  const [text, setText] = useState("");
  const [mapping, setMapping] = useState<Record<string, string>>({});
  const [metadata, setMetadata] = useState<{ fields: string[]; columns: string[] } | null>(null);
  const [preview, setPreview] = useState<ImportPreview | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState<number | null>(null);
  const [attempt, setAttempt] = useState(0);
  const locale = i18n.language === "en" ? "en" : "pt-PT";

  useEffect(() => {
    let active = true;
    void vehicles.list().then((rows) => { if (active) { setList(rows); setVehicleId((id) => id || rows[0]?.id || ""); } }).catch(() => { if (active) setError(t("common.error")); });
    return () => { active = false; };
  }, [t, attempt]);

  async function inspect(commit = false) {
    if (commit && !window.confirm(t("import.confirm", { count: preview?.rows.length }))) return;
    setBusy(true); setError(null);
    try {
      const payload = { vehicle_id: vehicleId, kind, csv_text: text, mapping, locale } as const;
      const result = await (commit ? imports.commit(payload) : imports.preview(payload));
      setMetadata({ fields: result.fields, columns: result.columns });
      setPreview(result);
      if (commit) setDone(result.imported);
    } catch { setError(t("import.failed")); }
    finally { setBusy(false); }
  }

  function invalidate() { setPreview(null); setDone(null); }
  const valid = preview && !preview.errors.length && preview.rows.every((row) => !row.errors.length);
  if (me?.membership.role === "reader") return <p>{t("import.readOnly")}</p>;
  return <div className="space-y-5">
    <h1 className="text-2xl font-bold">{t("import.title")}</h1>
    <p className="text-sm text-ink-muted">{t("import.description")}</p>
    {error && <p role="alert" className="text-sm text-red-700">{error}<button className="ml-2 underline" onClick={() => { setError(null); setAttempt((value) => value + 1); }}>{t("common.retry")}</button></p>}
    {done !== null && <p role="status" className="rounded-lg bg-emerald-50 p-3 text-emerald-800">{t("import.done", { count: done })} <Link className="underline" to={`/vehicles/${vehicleId}?section=${kind}`}>{t("import.openVehicle")}</Link></p>}
    <fieldset disabled={busy} className="grid gap-4 rounded-xl border border-line bg-raised p-4 sm:grid-cols-2">
      <label className="text-sm">{t("search.vehicleFilter")}<select value={vehicleId} onChange={(event) => { setVehicleId(event.target.value); invalidate(); }} className={input}><option value="" disabled>{t("import.chooseVehicle")}</option>{list.map((vehicle) => <option key={vehicle.id} value={vehicle.id}>{vehicle.name}</option>)}</select></label>
      <label className="text-sm">{t("search.kindFilter")}<select value={kind} onChange={(event) => { setKind(event.target.value as ImportKind); setMapping({}); setMetadata(null); invalidate(); }} className={input}>{(["fuel", "work", "expenses", "odometer", "notes"] as ImportKind[]).map((value) => <option key={value} value={value}>{t(`${value}.title`)}</option>)}</select></label>
      <a href={`/api/imports/${kind}/template.csv?locale=${locale}`} className="text-sm font-semibold text-copper sm:col-span-2">{t("import.template")}</a>
      <label className="text-sm sm:col-span-2">{t("import.file")}<input type="file" accept=".csv,text/csv" className={input} onChange={(event) => {
        const file = event.target.files?.[0];
        if (!file) return;
        invalidate(); setMapping({}); setMetadata(null); setText(""); setError(null);
        if (file.size > 1_000_000) { setError(t("import.tooLarge")); return; }
        setBusy(true);
        void file.text().then(setText).catch(() => setError(t("common.error"))).finally(() => setBusy(false));
      }} /></label>
      <label className="text-sm sm:col-span-2">{t("import.content")}<textarea rows={6} maxLength={1_000_000} value={text} onChange={(event) => { setText(event.target.value); setMapping({}); setMetadata(null); invalidate(); }} className={`${input} font-mono text-xs`} /></label>
      {metadata && <div className="sm:col-span-2"><h2 className="mb-3 font-semibold">{t("import.mapping")}</h2><div className="grid gap-3 sm:grid-cols-2">{metadata.fields.map((field) => <label key={field} className="text-sm">{t(`import.fields.${field}`)}<select className={input} value={mapping[field] ?? (metadata.columns.includes(field) ? field : "")} onChange={(event) => { setMapping((current) => ({ ...current, [field]: event.target.value })); invalidate(); }}><option value="">{t("import.ignore")}</option>{metadata.columns.map((column) => <option key={column} value={column}>{column}</option>)}</select></label>)}</div></div>}
      <button disabled={!vehicleId || !text.trim()} onClick={() => void inspect()} className="rounded-lg border border-copper/30 px-4 py-2 font-semibold text-copper disabled:opacity-60 sm:col-span-2">{busy ? t("common.loading") : t("import.preview")}</button>
    </fieldset>
    {preview && <section className="space-y-3">
      <h2 className="font-semibold">{t("import.previewCount", { count: preview.rows.length })}</h2>
      {preview.already_imported && <p role="status">{t("import.alreadyImported")}</p>}
      {preview.errors.map((message) => <p key={message} role="alert" className="text-sm text-red-700">{message}</p>)}
      <div className="max-h-96 overflow-auto rounded-lg border border-line"><table className="w-full text-left text-sm"><thead><tr><th className="p-3">{t("import.line")}</th><th className="p-3">{t("import.values")}</th><th className="p-3">{t("import.validation")}</th></tr></thead><tbody>{preview.rows.map((row) => <tr key={row.line} className="border-t border-line"><td className="p-3">{row.line}</td><td className="p-3"><dl>{Object.entries(row.data).filter(([,value]) => value !== null).map(([field,value]) => <div key={field}><dt className="inline font-medium">{t(`import.fields.${field}`)}: </dt><dd className="inline break-words">{String(value)}</dd></div>)}</dl></td><td className="p-3">{row.errors.length ? <ul className="text-red-700">{row.errors.map((message) => <li key={message}>{message}</li>)}</ul> : t("import.valid")}</td></tr>)}</tbody></table></div>
      <button disabled={busy || !valid || done !== null || preview.already_imported} onClick={() => void inspect(true)} className="rounded-lg bg-copper px-4 py-2 font-semibold text-white disabled:opacity-60">{t("import.commit", { count: preview.rows.length })}</button>
    </section>}
  </div>;
}
