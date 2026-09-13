import { useState } from "react";
import type { FormEvent } from "react";
import { useTranslation } from "react-i18next";

import { expenses } from "../../lib/api";
import { ApiError } from "../../lib/api/client";
import type { ExpenseRecord, ExpenseStatus } from "../../lib/api/types";

export function ExpensesSection({ records, vehicleId, onCreated }: { records: ExpenseRecord[]; vehicleId: string; onCreated: () => void }) {
  const { t, i18n } = useTranslation();
  const [open, setOpen] = useState(false);
  const [category, setCategory] = useState("insurance");
  const [amount, setAmount] = useState("");
  const [supplier, setSupplier] = useState("");
  const [expenseStatus, setExpenseStatus] = useState<ExpenseStatus>("paid");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const total = records.filter((record) => record.status === "paid").reduce((sum, record) => sum + Number(record.amount), 0);

  async function submit(event: FormEvent) {
    event.preventDefault(); setSaving(true); setError(null);
    try {
      await expenses.create(vehicleId, { issued_on: new Date().toISOString().slice(0, 10), category, amount: amount.replace(",", "."), supplier: supplier || undefined, status: expenseStatus });
      setOpen(false); setAmount(""); setSupplier(""); onCreated();
    } catch (cause) { setError(cause instanceof ApiError ? cause.message : t("common.error")); }
    finally { setSaving(false); }
  }

  return <section className="space-y-4 rounded-xl border border-slate-200 bg-white p-4 shadow-sm sm:p-6">
    <div className="flex items-center justify-between gap-4"><div><h2 className="text-lg font-semibold text-slate-900">{t("expenses.title")}</h2><p className="text-sm text-slate-500">{t("expenses.total", { value: total.toLocaleString(i18n.language, { style: "currency", currency: "EUR" }) })}</p></div><button onClick={() => setOpen((value) => !value)} className="rounded-md bg-[#B94A22] px-3 py-2 text-sm font-medium text-white">{t("expenses.add")}</button></div>
    {open && <form onSubmit={submit} className="grid gap-3 rounded-lg bg-slate-50 p-4 sm:grid-cols-2"><select value={category} onChange={(event) => setCategory(event.target.value)} className="rounded-md border border-slate-300 bg-white px-3 py-2"><option value="insurance">{t("expenses.insurance")}</option><option value="tax">{t("expenses.tax")}</option><option value="inspection">{t("expenses.inspection")}</option><option value="tolls">{t("expenses.tolls")}</option><option value="other">{t("expenses.other")}</option></select><input required inputMode="decimal" placeholder={t("expenses.amount")} value={amount} onChange={(event) => setAmount(event.target.value)} className="rounded-md border border-slate-300 bg-white px-3 py-2" /><input placeholder={t("expenses.supplier")} value={supplier} onChange={(event) => setSupplier(event.target.value)} className="rounded-md border border-slate-300 bg-white px-3 py-2" /><select value={expenseStatus} onChange={(event) => setExpenseStatus(event.target.value as ExpenseStatus)} className="rounded-md border border-slate-300 bg-white px-3 py-2"><option value="paid">{t("expenses.paid")}</option><option value="pending">{t("expenses.pending")}</option><option value="planned">{t("expenses.planned")}</option></select>{error && <p className="text-sm text-red-700 sm:col-span-2">{error}</p>}<button disabled={saving} className="rounded-md bg-[#B94A22] px-4 py-2 text-sm font-medium text-white disabled:opacity-60 sm:col-span-2">{t("garage.save")}</button></form>}
    {records.length === 0 ? <p className="text-sm text-slate-500">{t("expenses.empty")}</p> : <ul className="divide-y divide-slate-100">{records.map((record) => <li key={record.id} className="flex justify-between gap-4 py-3"><div><p className="font-medium text-slate-900">{t(`expenses.${record.category}`)}</p><p className="text-sm text-slate-500">{record.supplier || t(`expenses.${record.status}`)}</p></div><p className="text-sm font-medium text-slate-700">{Number(record.amount).toLocaleString(i18n.language, { style: "currency", currency: "EUR" })}</p></li>)}</ul>}
  </section>;
}
