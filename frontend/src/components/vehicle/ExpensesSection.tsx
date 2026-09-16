import { useState } from "react";
import type { FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { expenses } from "../../lib/api";
import { ApiError } from "../../lib/api/client";
import type { ExpenseRecord, ExpenseRecordInput, ExpenseStatus } from "../../lib/api/types";
import { useSession } from "../../lib/session";

function blank(): ExpenseRecordInput {
  const today = new Date();
  return { issued_on: `${today.getFullYear()}-${String(today.getMonth()+1).padStart(2,"0")}-${String(today.getDate()).padStart(2,"0")}`, category: "insurance", amount: "", status: "paid", supplier: "" };
}
export function ExpensesSection({ records, vehicleId, onCreated }: { records: ExpenseRecord[]; vehicleId: string; onCreated: () => void }) {
  const { t, i18n } = useTranslation();
  const { me } = useSession();
  const canWrite = me?.membership.role !== "reader";
  const [form, setForm] = useState<ExpenseRecordInput | null>(null);
  const [editing, setEditing] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const currency = (value: number) => value.toLocaleString(i18n.language, { style: "currency", currency: "EUR" });
  const total = records.filter((record) => record.status === "paid").reduce((sum, record) => sum + Number(record.amount), 0);
  const input = "mt-1 w-full rounded-lg border border-graphite/15 px-3 py-2 dark:border-white/15 dark:bg-surface-dark";
  async function submit(event: FormEvent) {
    event.preventDefault(); if (!form) return;
    setSaving(true); setError(null);
    try {
      const payload = { ...form, amount: form.amount.replace(",", ".") };
      if (editing) await expenses.update(vehicleId, editing, payload);
      else await expenses.create(vehicleId, payload);
      setForm(null); setEditing(null); onCreated();
    } catch (cause) { setError(cause instanceof ApiError ? cause.message : t("common.error")); }
    finally { setSaving(false); }
  }
  return <section className="space-y-4 rounded-xl border border-graphite/10 bg-white p-4 dark:border-white/10 dark:bg-surface-dark-raised">
    <div className="flex flex-wrap items-center justify-between gap-3"><div><h2 className="text-lg font-semibold">{t("expenses.title")}</h2><p className="text-sm text-graphite/60 dark:text-cream/60">{t("expenses.total", { value: currency(total) })}</p></div>{canWrite && <button onClick={() => { setForm(blank()); setEditing(null); }} className="rounded-lg bg-copper px-3 py-2 font-semibold text-white">{t("expenses.add")}</button>}</div>
    {error && <p role="alert" className="text-sm text-red-700">{error}</p>}
    {form && <form onSubmit={submit}><fieldset disabled={saving} className="grid gap-3 sm:grid-cols-2">
      <label className="text-sm">{t("import.fields.issued_on")}<input type="date" required value={form.issued_on} onChange={(event) => setForm({ ...form, issued_on: event.target.value })} className={input} /></label>
      <label className="text-sm">{t("import.fields.category")}<select value={["insurance", "tax", "inspection", "tolls", "other"].includes(form.category) ? form.category : "custom"} onChange={(event) => setForm({ ...form, category: event.target.value === "custom" ? "" : event.target.value })} className={input}>{["insurance", "tax", "inspection", "tolls", "other"].map((value) => <option key={value} value={value}>{t(`expenses.${value}`)}</option>)}<option value="custom">{t("recordActions.customCategory")}</option></select>{!["insurance", "tax", "inspection", "tolls", "other"].includes(form.category) && <input aria-label={t("recordActions.customCategory")} required maxLength={50} value={form.category} onChange={(event) => setForm({ ...form, category: event.target.value })} className={input} />}</label>
      <label className="text-sm">{t("expenses.amount")}<input required inputMode="decimal" value={form.amount} onChange={(event) => setForm({ ...form, amount: event.target.value })} className={input} /></label>
      <label className="text-sm">{t("expenses.supplier")}<input maxLength={200} value={form.supplier ?? ""} onChange={(event) => setForm({ ...form, supplier: event.target.value })} className={input} /></label>
      <label className="text-sm sm:col-span-2">{t("import.fields.status")}<select value={form.status} onChange={(event) => setForm({ ...form, status: event.target.value as ExpenseStatus })} className={input}>{(["paid", "pending", "planned", "cancelled"] as const).map((value) => <option key={value} value={value}>{t(`expenses.${value}`, { defaultValue: t("recordActions.cancelled") })}</option>)}</select></label>
      <button className="rounded-lg bg-copper px-4 py-2 font-semibold text-white">{t("garage.save")}</button><button type="button" onClick={() => setForm(null)} className="rounded-lg border px-4 py-2">{t("common.cancel")}</button>
    </fieldset></form>}
    {!records.length ? <p className="text-sm">{t("expenses.empty")}</p> : <ul className="divide-y divide-graphite/10 dark:divide-white/10">{records.map((record) => <li key={record.id} className="flex flex-wrap items-center justify-between gap-3 py-3">
      <div className="min-w-0"><p className="break-words font-semibold">{t(`expenses.${record.category}`, { defaultValue: record.category })}</p><p className="text-sm">{new Intl.DateTimeFormat(i18n.language).format(new Date(`${record.issued_on}T12:00:00`))} · {t(`expenses.${record.status}`, { defaultValue: t("recordActions.cancelled") })}{record.supplier ? ` · ${record.supplier}` : ""}</p></div>
      <div className="flex items-center gap-3"><span className="font-medium">{currency(Number(record.amount))}</span>{canWrite && <><button disabled={saving} className="text-sm text-copper" onClick={() => { setForm({ issued_on: record.issued_on, category: record.category, amount: record.amount, supplier: record.supplier ?? "", status: record.status }); setEditing(record.id); }}>{t("common.edit")}</button><button disabled={saving} className="text-sm text-red-700" onClick={() => {
        if (!window.confirm(t("common.confirmDelete"))) return;
        setSaving(true); setError(null);
        void expenses.remove(vehicleId, record.id).then(() => { if (editing === record.id) setForm(null); onCreated(); }).catch(() => setError(t("common.error"))).finally(() => setSaving(false));
      }}>{t("common.delete")}</button></>}</div>
    </li>)}</ul>}
  </section>;
}
