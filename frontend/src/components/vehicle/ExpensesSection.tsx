import { useState } from "react";
import type { FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { expenses } from "../../lib/api";
import { ApiError } from "../../lib/api/client";
import type {
  ExpenseRecord,
  ExpenseRecordInput,
  ExpenseStatus,
  ExpenseStatusOut,
  RecurrenceUnit,
} from "../../lib/api/types";
import { useSession } from "../../lib/session";
import { useConfirm } from "../../components/ui/confirm-context";

const PRESET_CATEGORIES = ["insurance", "tax", "inspection", "tolls", "other"];
const STATUSES: ExpenseStatus[] = ["paid", "pending", "planned", "cancelled"];
const UNITS: RecurrenceUnit[] = ["day", "month", "year"];

function today(): string {
  const now = new Date();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${now.getFullYear()}-${month}-${day}`;
}

function blank(): ExpenseRecordInput {
  return { issued_on: today(), category: "insurance", amount: "", status: "paid", supplier: "" };
}

/**
 * "overdue" is derived by the server and cannot be sent back, so an overdue
 * record edits as what it really is: pending, past its due date.
 */
function submittableStatus(status: ExpenseStatusOut): ExpenseStatus {
  return status === "overdue" ? "pending" : status;
}

function formFrom(record: ExpenseRecord): ExpenseRecordInput {
  return {
    issued_on: record.issued_on,
    category: record.category,
    amount: record.amount,
    supplier: record.supplier ?? "",
    status: submittableStatus(record.status),
    due_on: record.due_on,
    paid_on: record.paid_on,
    reference: record.reference ?? "",
    notes: record.notes ?? "",
    recurrence_interval: record.recurrence_interval,
    recurrence_unit: record.recurrence_unit,
    recurrence_amount_varies: record.recurrence_amount_varies,
  };
}

export function ExpensesSection({
  records,
  vehicleId,
  onCreated,
}: {
  records: ExpenseRecord[];
  vehicleId: string;
  onCreated: () => void;
}) {
  const { t, i18n } = useTranslation();
  const confirm = useConfirm();
  const { me } = useSession();
  const canWrite = me?.membership.role !== "reader";
  const [form, setForm] = useState<ExpenseRecordInput | null>(null);
  const [editing, setEditing] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const currency = (value: number) =>
    value.toLocaleString(i18n.language, { style: "currency", currency: "EUR" });
  const total = records
    .filter((record) => record.status === "paid")
    .reduce((sum, record) => sum + Number(record.amount), 0);
  const input = "mt-1 w-full rounded-lg border border-line px-3 py-2 bg-raised";
  const recurs = Boolean(form?.recurrence_unit);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!form) return;
    setSaving(true);
    setError(null);
    try {
      const payload = {
        ...form,
        amount: form.amount.replace(",", "."),
        due_on: form.due_on || null,
        paid_on: form.paid_on || null,
      };
      if (editing) await expenses.update(vehicleId, editing, payload);
      else await expenses.create(vehicleId, payload);
      setForm(null);
      setEditing(null);
      onCreated();
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : t("common.error"));
    } finally {
      setSaving(false);
    }
  }

  async function raiseNext(record: ExpenseRecord) {
    setSaving(true);
    setError(null);
    try {
      await expenses.nextOccurrence(vehicleId, record.id);
      onCreated();
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : t("common.error"));
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="space-y-4 rounded-xl border border-line bg-raised p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold">{t("expenses.title")}</h2>
          <p className="text-sm text-ink-muted">
            {t("expenses.total", { value: currency(total) })}
          </p>
        </div>
        {canWrite && (
          <button
            onClick={() => {
              setForm(blank());
              setEditing(null);
            }}
            className="rounded-lg bg-copper px-3 py-2 font-semibold text-white"
          >
            {t("expenses.add")}
          </button>
        )}
      </div>

      {error && (
        <p role="alert" className="text-sm text-danger">
          {error}
        </p>
      )}

      {form && (
        <form onSubmit={submit}>
          <fieldset disabled={saving} className="grid gap-3 sm:grid-cols-2">
            <label className="text-sm">
              {t("import.fields.issued_on")}
              <input
                type="date"
                required
                value={form.issued_on}
                onChange={(event) => setForm({ ...form, issued_on: event.target.value })}
                className={input}
              />
            </label>
            <label className="text-sm">
              {t("import.fields.category")}
              <select
                value={PRESET_CATEGORIES.includes(form.category) ? form.category : "custom"}
                onChange={(event) =>
                  setForm({
                    ...form,
                    category: event.target.value === "custom" ? "" : event.target.value,
                  })
                }
                className={input}
              >
                {PRESET_CATEGORIES.map((value) => (
                  <option key={value} value={value}>
                    {t(`expenses.${value}`)}
                  </option>
                ))}
                <option value="custom">{t("recordActions.customCategory")}</option>
              </select>
              {!PRESET_CATEGORIES.includes(form.category) && (
                <input
                  aria-label={t("recordActions.customCategory")}
                  required
                  maxLength={50}
                  value={form.category}
                  onChange={(event) => setForm({ ...form, category: event.target.value })}
                  className={input}
                />
              )}
            </label>
            <label className="text-sm">
              {t("expenses.amount")}
              <input
                required
                inputMode="decimal"
                value={form.amount}
                onChange={(event) => setForm({ ...form, amount: event.target.value })}
                className={input}
              />
            </label>
            <label className="text-sm">
              {t("expenses.supplier")}
              <input
                maxLength={200}
                value={form.supplier ?? ""}
                onChange={(event) => setForm({ ...form, supplier: event.target.value })}
                className={input}
              />
            </label>
            <label className="text-sm">
              {t("expenses.dueOn")}
              <input
                type="date"
                value={form.due_on ?? ""}
                onChange={(event) => setForm({ ...form, due_on: event.target.value })}
                className={input}
              />
            </label>
            <label className="text-sm">
              {t("expenses.paidOn")}
              <input
                type="date"
                value={form.paid_on ?? ""}
                onChange={(event) => setForm({ ...form, paid_on: event.target.value })}
                className={input}
              />
            </label>
            <label className="text-sm">
              {t("expenses.reference")}
              <input
                maxLength={100}
                value={form.reference ?? ""}
                onChange={(event) => setForm({ ...form, reference: event.target.value })}
                className={input}
              />
            </label>
            <label className="text-sm">
              {t("import.fields.status")}
              <select
                value={form.status}
                onChange={(event) =>
                  setForm({ ...form, status: event.target.value as ExpenseStatus })
                }
                className={input}
              >
                {STATUSES.map((value) => (
                  <option key={value} value={value}>
                    {t(`expenses.${value}`, { defaultValue: t("recordActions.cancelled") })}
                  </option>
                ))}
              </select>
            </label>
            <label className="text-sm sm:col-span-2">
              {t("expenses.notes")}
              <textarea
                maxLength={2000}
                rows={2}
                value={form.notes ?? ""}
                onChange={(event) => setForm({ ...form, notes: event.target.value })}
                className={input}
              />
            </label>

            <fieldset className="rounded-lg border border-line p-3 sm:col-span-2">
              <legend className="px-1 text-sm font-medium">{t("expenses.recurrence")}</legend>
              <div className="grid gap-3 sm:grid-cols-3">
                <label className="text-sm">
                  {t("expenses.recurrenceUnit")}
                  <select
                    value={form.recurrence_unit ?? ""}
                    onChange={(event) =>
                      setForm({
                        ...form,
                        recurrence_unit: (event.target.value || null) as RecurrenceUnit | null,
                        // An interval without a unit says nothing about when, and
                        // the API refuses one half without the other.
                        recurrence_interval: event.target.value
                          ? (form.recurrence_interval ?? 1)
                          : null,
                      })
                    }
                    className={input}
                  >
                    <option value="">{t("expenses.recurrenceNone")}</option>
                    {UNITS.map((unit) => (
                      <option key={unit} value={unit}>
                        {t(`expenses.recurrenceUnits.${unit}`)}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="text-sm">
                  {t("expenses.recurrenceInterval")}
                  <input
                    type="number"
                    min={1}
                    max={120}
                    disabled={!recurs}
                    value={form.recurrence_interval ?? ""}
                    onChange={(event) =>
                      setForm({ ...form, recurrence_interval: Number(event.target.value) || null })
                    }
                    className={input}
                  />
                </label>
                <label className="flex items-end gap-2 text-sm">
                  <input
                    type="checkbox"
                    disabled={!recurs}
                    checked={form.recurrence_amount_varies ?? false}
                    onChange={(event) =>
                      setForm({ ...form, recurrence_amount_varies: event.target.checked })
                    }
                    className="mb-3"
                  />
                  <span className="mb-2.5">{t("expenses.recurrenceVaries")}</span>
                </label>
              </div>
            </fieldset>

            <button className="rounded-lg bg-copper px-4 py-2 font-semibold text-white">
              {t("garage.save")}
            </button>
            <button
              type="button"
              onClick={() => setForm(null)}
              className="rounded-lg border px-4 py-2"
            >
              {t("common.cancel")}
            </button>
          </fieldset>
        </form>
      )}

      {!records.length ? (
        <p className="text-sm">{t("expenses.empty")}</p>
      ) : (
        <ul className="divide-y divide-graphite/10 dark:divide-white/10">
          {records.map((record) => (
            <li key={record.id} className="flex flex-wrap items-center justify-between gap-3 py-3">
              <div className="min-w-0">
                <p className="break-words font-semibold">
                  {t(`expenses.${record.category}`, { defaultValue: record.category })}
                  {record.reference && (
                    <span className="ml-2 text-xs font-normal text-ink-subtle">
                      {record.reference}
                    </span>
                  )}
                </p>
                <p className="text-sm">
                  {new Intl.DateTimeFormat(i18n.language).format(
                    new Date(`${record.issued_on}T12:00:00`),
                  )}{" "}
                  ·{" "}
                  <span className={record.status === "overdue" ? "font-semibold text-danger" : ""}>
                    {t(`expenses.${record.status}`, { defaultValue: t("recordActions.cancelled") })}
                  </span>
                  {record.supplier ? ` · ${record.supplier}` : ""}
                </p>
              </div>
              <div className="flex items-center gap-3">
                <span className="font-medium">{currency(Number(record.amount))}</span>
                {canWrite && (
                  <>
                    {record.recurrence_unit && (
                      <button
                        disabled={saving}
                        className="text-sm text-copper"
                        onClick={() => void raiseNext(record)}
                      >
                        {t("expenses.nextOccurrence")}
                      </button>
                    )}
                    <button
                      disabled={saving}
                      className="text-sm text-copper"
                      onClick={() => {
                        setForm(formFrom(record));
                        setEditing(record.id);
                      }}
                    >
                      {t("common.edit")}
                    </button>
                    <button
                      disabled={saving}
                      className="text-sm text-danger"
                      onClick={async () => {
                        if (!await confirm(t("common.confirmDelete"))) return;
                        setSaving(true);
                        setError(null);
                        void expenses
                          .remove(vehicleId, record.id)
                          .then(() => {
                            if (editing === record.id) setForm(null);
                            onCreated();
                          })
                          .catch(() => setError(t("common.error")))
                          .finally(() => setSaving(false));
                      }}
                    >
                      {t("common.delete")}
                    </button>
                  </>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
