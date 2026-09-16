import { useState } from "react";
import type { FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { TrashIcon } from "@heroicons/react/24/outline";

import { fuel } from "../../lib/api";
import { ApiError } from "../../lib/api/client";
import type { FuelRecord } from "../../lib/api/types";
export function FuelSection({
  records,
  vehicleId,
  currentReading,
  onCreated,
}: {
  records: FuelRecord[];
  vehicleId: string;
  currentReading: number | null;
  onCreated: () => void;
}) {
  const { t, i18n } = useTranslation();
  const [showForm, setShowForm] = useState(false);
  const formatDate = (value: string) =>
    new Intl.DateTimeFormat(i18n.language).format(
      new Date(`${value}T12:00:00`),
    );

  return (
    <section className="space-y-4 rounded-xl border border-line bg-raised p-4 shadow-sm sm:p-6">
      <div className="flex flex-col items-stretch gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-lg font-semibold text-ink">
            {t("fuel.title")}
          </h2>
          <p className="text-sm text-ink-subtle">{t("fuel.description")}</p>
        </div>
        <button
          onClick={() => setShowForm((value) => !value)}
          className="self-start rounded-md bg-copper px-3 py-2 text-sm font-medium text-white hover:bg-copper-dark"
        >
          {t("fuel.add")}
        </button>
      </div>
      {showForm && (
        <FuelForm
          vehicleId={vehicleId}
          currentReading={currentReading}
          onCreated={() => {
            setShowForm(false);
            onCreated();
          }}
        />
      )}
      {records.length === 0 ? (
        <p className="py-4 text-sm text-ink-subtle">{t("fuel.empty")}</p>
      ) : (
        <ul className="divide-y divide-line">
          {records.map((record) => (
            <li
              key={record.id}
              className="flex min-w-0 flex-col gap-2 py-3 sm:flex-row sm:items-center sm:justify-between sm:gap-4"
            >
              <div className="min-w-0">
                <p className="font-medium text-ink">
                  {Number(record.volume_litres).toLocaleString(i18n.language)} L
                  ·{" "}
                  {Number(record.total_price).toLocaleString(i18n.language, {
                    style: "currency",
                    currency: "EUR",
                  })}
                </p>
                <p className="break-words text-sm text-ink-subtle">
                  {formatDate(record.recorded_on)}
                  {record.station ? ` · ${record.station}` : ""}
                </p>
              </div>
              <div className="flex items-center gap-3">
                <p className="text-sm text-ink-subtle">
                  {record.consumption_l_per_100km
                    ? `${Number(record.consumption_l_per_100km).toLocaleString(i18n.language, { maximumFractionDigits: 1 })} L/100 km`
                    : "—"}
                </p>
                <button
                  onClick={() => {
                    if (window.confirm(t("common.confirmDelete")))
                      void fuel.remove(vehicleId, record.id).then(onCreated);
                  }}
                  className="flex items-center gap-1 text-xs font-medium text-danger"
                >
                  <TrashIcon aria-hidden="true" className="h-3.5 w-3.5" />
                  {t("common.delete")}
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function FuelForm({
  vehicleId,
  currentReading,
  onCreated,
}: {
  vehicleId: string;
  currentReading: number | null;
  onCreated: () => void;
}) {
  const { t } = useTranslation();
  const [recordedOn, setRecordedOn] = useState(
    new Date().toISOString().slice(0, 10),
  );
  const [odometerReading, setOdometerReading] = useState(
    currentReading?.toString() ?? "",
  );
  const [volume, setVolume] = useState("");
  const [totalPrice, setTotalPrice] = useState("");
  const [station, setStation] = useState("");
  const [fullTank, setFullTank] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const decimal = (value: string) => value.replace(",", ".");

  async function submit(event: FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await fuel.create(vehicleId, {
        recorded_on: recordedOn,
        odometer_reading: odometerReading ? Number(odometerReading) : undefined,
        volume_litres: decimal(volume),
        total_price: decimal(totalPrice),
        station: station || undefined,
        full_tank: fullTank,
      });
      onCreated();
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : t("common.error"));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form
      onSubmit={submit}
      className="grid gap-3 rounded-lg bg-sunken p-4 sm:grid-cols-2"
    >
      <label className="text-sm">
        <span className="mb-1 block font-medium text-ink-muted">
          {t("fuel.date")}
        </span>
        <input
          required
          type="date"
          value={recordedOn}
          onChange={(event) => setRecordedOn(event.target.value)}
          className="w-full rounded-md border border-line bg-raised px-3 py-2"
        />
      </label>
      <label className="text-sm">
        <span className="mb-1 block font-medium text-ink-muted">
          {t("fuel.odometer")}
        </span>
        <input
          min="0"
          inputMode="numeric"
          type="number"
          value={odometerReading}
          onChange={(event) => setOdometerReading(event.target.value)}
          className="w-full rounded-md border border-line bg-raised px-3 py-2"
        />
      </label>
      <label className="text-sm">
        <span className="mb-1 block font-medium text-ink-muted">
          {t("fuel.volume")}
        </span>
        <input
          required
          min="0.001"
          step="0.001"
          inputMode="decimal"
          type="text"
          value={volume}
          onChange={(event) => setVolume(event.target.value)}
          className="w-full rounded-md border border-line bg-raised px-3 py-2"
        />
      </label>
      <label className="text-sm">
        <span className="mb-1 block font-medium text-ink-muted">
          {t("fuel.total")}
        </span>
        <input
          required
          min="0"
          step="0.01"
          inputMode="decimal"
          type="text"
          value={totalPrice}
          onChange={(event) => setTotalPrice(event.target.value)}
          className="w-full rounded-md border border-line bg-raised px-3 py-2"
        />
      </label>
      <label className="text-sm sm:col-span-2">
        <span className="mb-1 block font-medium text-ink-muted">
          {t("fuel.station")}
        </span>
        <input
          value={station}
          onChange={(event) => setStation(event.target.value)}
          className="w-full rounded-md border border-line bg-raised px-3 py-2"
        />
      </label>
      <label className="flex items-center gap-2 text-sm text-ink-muted sm:col-span-2">
        <input
          type="checkbox"
          checked={fullTank}
          onChange={(event) => setFullTank(event.target.checked)}
        />
        {t("fuel.fullTank")}
      </label>
      {error && <p className="text-sm text-danger sm:col-span-2">{error}</p>}
      <button
        type="submit"
        disabled={submitting}
        className="rounded-md bg-copper px-4 py-2 text-sm font-medium text-white hover:bg-copper-dark disabled:opacity-60 sm:col-span-2"
      >
        {t("garage.save")}
      </button>
    </form>
  );
}
