import { useState } from "react";
import type { FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { TrashIcon } from "@heroicons/react/24/outline";

import { workRecords } from "../../lib/api";
import { ApiError } from "../../lib/api/client";
import type { WorkKind, WorkRecord } from "../../lib/api/types";
export function WorkSection({
  records,
  vehicleId,
  currentReading,
  onCreated,
}: {
  records: WorkRecord[];
  vehicleId: string;
  currentReading: number | null;
  onCreated: () => void;
}) {
  const { t, i18n } = useTranslation();
  const [show, setShow] = useState(false);
  const [description, setDescription] = useState("");
  const [cost, setCost] = useState("");
  const [kind, setKind] = useState<WorkKind>("maintenance");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  async function submit(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    try {
      await workRecords.create(vehicleId, {
        recorded_on: new Date().toISOString().slice(0, 10),
        kind,
        description,
        total_cost: cost.replace(",", ".") || undefined,
        odometer_reading: currentReading ?? undefined,
      });
      setShow(false);
      setDescription("");
      setCost("");
      onCreated();
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : t("common.error"));
    } finally {
      setSaving(false);
    }
  }
  async function remove(id: string) {
    if (window.confirm(t("common.confirmDelete"))) {
      await workRecords.remove(vehicleId, id);
      onCreated();
    }
  }
  return (
    <section className="space-y-4 rounded-xl border border-line bg-raised p-4 shadow-sm sm:p-6">
      <div className="flex flex-col items-stretch gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-lg font-semibold text-ink">
            {t("work.title")}
          </h2>
          <p className="text-sm text-slate-500">{t("work.description")}</p>
        </div>
        <button
          onClick={() => setShow((value) => !value)}
          className="self-start rounded-md bg-copper px-3 py-2 text-sm font-medium text-white hover:bg-copper-dark"
        >
          {t("work.add")}
        </button>
      </div>
      {show && (
        <form
          onSubmit={submit}
          className="grid gap-3 rounded-lg bg-sunken p-4 sm:grid-cols-2"
        >
          <select
            value={kind}
            onChange={(event) => setKind(event.target.value as WorkKind)}
            className="rounded-md border border-line bg-raised px-3 py-2"
          >
            <option value="maintenance">{t("work.maintenance")}</option>
            <option value="repair">{t("work.repair")}</option>
            <option value="modification">{t("work.modification")}</option>
          </select>
          <input
            required
            placeholder={t("work.placeholder")}
            value={description}
            onChange={(event) => setDescription(event.target.value)}
            className="rounded-md border border-line bg-raised px-3 py-2"
          />
          <input
            inputMode="decimal"
            placeholder={t("work.cost")}
            value={cost}
            onChange={(event) => setCost(event.target.value)}
            className="rounded-md border border-line bg-raised px-3 py-2"
          />
          {error && <p className="text-sm text-red-700">{error}</p>}
          <button
            disabled={saving}
            className="rounded-md bg-copper px-4 py-2 text-sm font-medium text-white disabled:opacity-60"
          >
            {t("garage.save")}
          </button>
        </form>
      )}
      <ul className="divide-y divide-slate-100">
        {records.map((record) => (
          <li
            key={record.id}
            className="flex min-w-0 flex-col gap-2 py-3 sm:flex-row sm:justify-between sm:gap-4"
          >
            <div className="min-w-0">
              <p className="break-words font-medium text-ink">
                {record.description}
              </p>
              <p className="text-sm text-slate-500">
                {t(`work.${record.kind}`)}
                {record.supplier ? ` · ${record.supplier}` : ""}
              </p>
            </div>
            <div className="flex shrink-0 items-center gap-3">
              <p className="text-sm text-slate-500">
                {record.total_cost
                  ? Number(record.total_cost).toLocaleString(i18n.language, {
                      style: "currency",
                      currency: "EUR",
                    })
                  : "—"}
              </p>
              <button
                onClick={() => void remove(record.id)}
                className="flex items-center gap-1 text-xs font-medium text-red-700"
              >
                <TrashIcon aria-hidden="true" className="h-3.5 w-3.5" />
                {t("common.delete")}
              </button>
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}
