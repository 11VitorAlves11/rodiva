import { useState } from "react";
import type { FormEvent } from "react";
import { useTranslation } from "react-i18next";

import { odometer } from "../../lib/api";
import { ApiError } from "../../lib/api/client";
import type { OdometerReading } from "../../lib/api/types";
export function OdometerForm({
  vehicleId,
  unit,
  onCreated,
}: {
  vehicleId: string;
  unit: string;
  onCreated: (reading: OdometerReading) => void;
}) {
  const { t } = useTranslation();
  const [recordedOn, setRecordedOn] = useState(
    new Date().toISOString().slice(0, 10),
  );
  const [reading, setReading] = useState("");
  const [notes, setNotes] = useState("");
  const [adjustment, setAdjustment] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      onCreated(
        await odometer.create(vehicleId, {
          recorded_on: recordedOn,
          reading: Number(reading),
          notes: notes || undefined,
          is_adjustment: adjustment,
        }),
      );
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
          {t("odometer.date")}
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
          {t("odometer.reading", { unit })}
        </span>
        <input
          required
          min="0"
          step="1"
          inputMode="numeric"
          type="number"
          value={reading}
          onChange={(event) => setReading(event.target.value)}
          className="w-full rounded-md border border-line bg-raised px-3 py-2"
        />
      </label>
      <label className="text-sm sm:col-span-2">
        <span className="mb-1 block font-medium text-ink-muted">
          {t("odometer.notes")}
        </span>
        <input
          value={notes}
          onChange={(event) => setNotes(event.target.value)}
          className="w-full rounded-md border border-line bg-raised px-3 py-2"
        />
      </label>
      <label className="flex items-center gap-2 text-sm text-ink-muted sm:col-span-2">
        <input
          type="checkbox"
          checked={adjustment}
          onChange={(event) => setAdjustment(event.target.checked)}
        />
        {t("odometer.adjustmentCheck")}
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
