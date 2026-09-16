import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { charging } from "../../lib/api";
import type { ChargingInput, ChargingRecord } from "../../lib/api/types";
import { useSession } from "../../lib/session";

const inputClass = "mt-1 w-full rounded-lg border border-line px-3 py-2 bg-raised";
function blank(): ChargingInput {
  const today = new Date();
  return { recorded_on: `${today.getFullYear()}-${String(today.getMonth()+1).padStart(2,"0")}-${String(today.getDate()).padStart(2,"0")}`, energy_kwh: "", total_cost: "", charger_type: "home" };
}

export function ChargingSection({ vehicleId, unit }: { vehicleId: string; unit: string }) {
  const { t, i18n } = useTranslation();
  const { me } = useSession();
  const canWrite = me?.membership.role !== "reader";
  const [rows, setRows] = useState<ChargingRecord[] | null>(null);
  const [form, setForm] = useState<ChargingInput | null>(null);
  const [editing, setEditing] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    let active = true;
    void charging.list(vehicleId).then((items) => { if (active) setRows(items); }).catch(() => { if (active) setError(t("common.error")); });
    return () => { active = false; };
  }, [vehicleId, attempt, t]);

  async function save(event: FormEvent) {
    event.preventDefault(); if (!form) return;
    setBusy(true); setError(null);
    const payload = { ...form, energy_kwh: form.energy_kwh.replace(",", "."), total_cost: form.total_cost.replace(",", ".") };
    try {
      if (editing) await charging.update(vehicleId, editing, payload);
      else await charging.create(vehicleId, payload);
      setForm(null); setEditing(null); setAttempt((value) => value + 1);
    } catch { setError(t("charging.invalid")); }
    finally { setBusy(false); }
  }
  const currency = (value: string) => Number(value).toLocaleString(i18n.language, { style: "currency", currency: "EUR" });
  return <section className="space-y-4 rounded-xl border border-line bg-raised p-4">
    <div className="flex flex-wrap items-center justify-between gap-3"><h2 className="text-lg font-semibold">{t("charging.title")}</h2>{canWrite && <button onClick={() => { setForm(blank()); setEditing(null); }} className="rounded-lg bg-copper px-4 py-2 font-semibold text-white">{t("charging.add")}</button>}</div>
    <p className="text-sm text-ink-muted">{t("charging.efficiencyHint")}</p>
    {error && <p role="alert" className="text-sm text-danger">{error}<button className="ml-2 underline" onClick={() => { setError(null); setAttempt((value) => value + 1); }}>{t("common.retry")}</button></p>}
    {form && <form onSubmit={save}><fieldset disabled={busy} className="grid gap-3 sm:grid-cols-2">
      <label className="text-sm">{t("import.fields.recorded_on")}<input type="date" required value={form.recorded_on} onChange={(event) => setForm({ ...form, recorded_on: event.target.value })} className={inputClass} /></label>
      <label className="text-sm">{t("import.fields.odometer_reading")} ({unit})<input type="number" min="0" max="9999999" value={form.odometer_reading ?? ""} onChange={(event) => setForm({ ...form, odometer_reading: event.target.value ? Number(event.target.value) : null })} className={inputClass} /></label>
      <label className="text-sm">{t("charging.energy")}<input required inputMode="decimal" value={form.energy_kwh} onChange={(event) => setForm({ ...form, energy_kwh: event.target.value })} className={inputClass} /></label>
      <label className="text-sm">{t("import.fields.total_cost")} (€)<input required inputMode="decimal" value={form.total_cost} onChange={(event) => setForm({ ...form, total_cost: event.target.value })} className={inputClass} /></label>
      {(["soc_start", "soc_end"] as const).map((field) => <label key={field} className="text-sm">{t(`charging.${field}`)} (%)<input type="number" min="0" max="100" value={form[field] ?? ""} onChange={(event) => setForm({ ...form, [field]: event.target.value ? Number(event.target.value) : null })} className={inputClass} /></label>)}
      <label className="text-sm">{t("charging.location")}<input maxLength={200} value={form.location ?? ""} onChange={(event) => setForm({ ...form, location: event.target.value })} className={inputClass} /></label>
      <label className="text-sm">{t("charging.chargerType")}<select value={["home", "public"].includes(form.charger_type) ? form.charger_type : "other"} onChange={(event) => setForm({ ...form, charger_type: event.target.value === "other" ? "" : event.target.value })} className={inputClass}><option value="home">{t("charging.home")}</option><option value="public">{t("charging.public")}</option><option value="other">{t("expenses.other")}</option></select>{!["home", "public"].includes(form.charger_type) && <input aria-label={t("charging.chargerType")} required maxLength={100} value={form.charger_type} onChange={(event) => setForm({ ...form, charger_type: event.target.value })} className={inputClass} />}</label>
      <label className="text-sm sm:col-span-2">{t("import.fields.notes")}<textarea maxLength={2000} value={form.notes ?? ""} onChange={(event) => setForm({ ...form, notes: event.target.value })} className={inputClass} /></label>
      <button className="rounded-lg bg-copper px-4 py-2 font-semibold text-white">{t("garage.save")}</button><button type="button" onClick={() => setForm(null)} className="rounded-lg border px-4 py-2">{t("common.cancel")}</button>
    </fieldset></form>}
    {!rows ? <p>{t("common.loading")}</p> : !rows.length ? <p className="text-sm">{t("charging.empty")}</p> : <ul className="divide-y divide-graphite/10 dark:divide-white/10">{rows.map((row) => <li key={row.id} className="flex flex-wrap justify-between gap-3 py-4">
      <div><p className="font-semibold">{Number(row.energy_kwh).toLocaleString(i18n.language)} kWh · {currency(row.total_cost)}</p><p className="text-sm">{new Intl.DateTimeFormat(i18n.language).format(new Date(`${row.recorded_on}T12:00:00`))} · {row.location || t(`charging.${row.charger_type}`, { defaultValue: row.charger_type })}</p><p className="text-sm">{currency(row.unit_price)} / kWh{row.odometer_reading !== null && row.odometer_reading !== undefined ? ` · ${row.odometer_reading.toLocaleString(i18n.language)} ${unit}` : ""}</p>{row.efficiency_kwh_per_100km && <p className="text-sm">{Number(row.efficiency_kwh_per_100km).toLocaleString(i18n.language, { maximumFractionDigits: 1 })} kWh/100 km · {(100 / Number(row.efficiency_kwh_per_100km)).toLocaleString(i18n.language, { maximumFractionDigits: 2 })} km/kWh</p>}</div>
      {canWrite && <div className="flex gap-3"><button disabled={busy} onClick={() => { const { recorded_on, energy_kwh, total_cost, odometer_reading, soc_start, soc_end, location, charger_type, notes } = row; setForm({ recorded_on, energy_kwh, total_cost, odometer_reading, soc_start, soc_end, location, charger_type, notes }); setEditing(row.id); }} className="text-sm text-copper">{t("common.edit")}</button><button disabled={busy} onClick={() => {
        if (!window.confirm(t("common.confirmDelete"))) return;
        setBusy(true); setError(null);
        void charging.remove(vehicleId, row.id).then(() => setAttempt((value) => value + 1)).catch(() => setError(t("common.error"))).finally(() => setBusy(false));
      }} className="text-sm text-danger">{t("common.delete")}</button></div>}
    </li>)}</ul>}
  </section>;
}
