import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { useTranslation } from "react-i18next";

import { Button } from "../ui/Button";
import { Field, Select } from "../ui/Field";
import { Skeleton } from "../ui/Skeleton";
import { notifications, vehicles } from "../../lib/api";
import { ApiError } from "../../lib/api/client";
import type { NotificationPreference, NotificationUrgency, Vehicle } from "../../lib/api/types";

const urgencies: NotificationUrgency[] = ["overdue", "very_urgent", "urgent", "upcoming", "future"];
const hours = Array.from({ length: 24 }, (_, hour) => hour);

export function NotificationSettings() {
  const { t } = useTranslation();
  const [preference, setPreference] = useState<NotificationPreference | null>(null);
  const [vehicleList, setVehicleList] = useState<Vehicle[]>([]);
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [quiet, setQuiet] = useState(false);

  useEffect(() => {
    Promise.all([notifications.preferences(), vehicles.list()])
      .then(([loaded, loadedVehicles]) => {
        setPreference(loaded);
        setVehicleList(loadedVehicles);
        setQuiet(loaded.quiet_hours_start !== null);
      })
      .catch(() => setError(t("common.error")));
  }, [t]);

  if (!preference) return <Skeleton lines={5} />;

  const update = (patch: Partial<NotificationPreference>) =>
    setPreference((current) => (current ? { ...current, ...patch } : current));

  const toggleVehicle = (id: string) =>
    update({
      vehicle_ids: preference.vehicle_ids.includes(id)
        ? preference.vehicle_ids.filter((item) => item !== id)
        : [...preference.vehicle_ids, id],
    });

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!preference) return;
    setSaving(true);
    setError(null);
    setStatus(null);
    try {
      const saved = await notifications.savePreferences({
        ...preference,
        quiet_hours_start: quiet ? (preference.quiet_hours_start ?? 22) : null,
        quiet_hours_end: quiet ? (preference.quiet_hours_end ?? 7) : null,
      });
      setPreference(saved);
      setStatus(t("notifications.saved"));
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : t("common.error"));
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={submit} className="space-y-4 rounded-xl border border-line bg-raised p-4 sm:p-6">
      <div>
        <h2 className="text-base font-semibold text-ink">{t("notifications.settingsTitle")}</h2>
        <p className="mt-0.5 text-sm text-ink-muted">{t("notifications.settingsDescription")}</p>
      </div>

      <fieldset className="space-y-2">
        <legend className="mb-1 text-sm font-medium text-ink-muted">
          {t("notifications.channels")}
        </legend>
        <label className="flex items-center gap-2 text-sm text-ink">
          <input
            type="checkbox"
            checked={preference.channel_inapp}
            onChange={(event) => update({ channel_inapp: event.target.checked })}
          />
          {t("notifications.channelInapp")}
        </label>
        <label className="flex items-center gap-2 text-sm text-ink">
          <input
            type="checkbox"
            checked={preference.channel_email}
            onChange={(event) => update({ channel_email: event.target.checked })}
          />
          {t("notifications.channelEmail")}
        </label>
        <p className="text-xs text-ink-subtle">{t("notifications.emailHint")}</p>
      </fieldset>

      <Field label={t("notifications.minUrgency")} hint={t("notifications.minUrgencyHint")}>
        <Select
          value={preference.min_urgency}
          onChange={(event) =>
            update({ min_urgency: event.target.value as NotificationUrgency })
          }
        >
          {urgencies.map((urgency) => (
            <option key={urgency} value={urgency}>
              {t(`reminders.${urgency}`, { defaultValue: urgency })}
            </option>
          ))}
        </Select>
      </Field>

      {vehicleList.length > 0 && (
        <fieldset>
          <legend className="mb-1 text-sm font-medium text-ink-muted">
            {t("notifications.vehicles")}
          </legend>
          <div className="flex flex-wrap gap-3">
            {vehicleList.map((vehicle) => (
              <label key={vehicle.id} className="flex items-center gap-2 text-sm text-ink">
                <input
                  type="checkbox"
                  checked={preference.vehicle_ids.includes(vehicle.id)}
                  onChange={() => toggleVehicle(vehicle.id)}
                />
                {vehicle.name}
              </label>
            ))}
          </div>
          <p className="mt-1 text-xs text-ink-subtle">{t("notifications.vehiclesHint")}</p>
        </fieldset>
      )}

      <fieldset className="space-y-2">
        <label className="flex items-center gap-2 text-sm text-ink">
          <input type="checkbox" checked={quiet} onChange={(event) => setQuiet(event.target.checked)} />
          {t("notifications.quietHours")}
        </label>
        {quiet && (
          <div className="grid gap-3 sm:grid-cols-2">
            <Field label={t("notifications.quietFrom")}>
              <Select
                value={String(preference.quiet_hours_start ?? 22)}
                onChange={(event) => update({ quiet_hours_start: Number(event.target.value) })}
              >
                {hours.map((hour) => (
                  <option key={hour} value={hour}>{`${String(hour).padStart(2, "0")}:00`}</option>
                ))}
              </Select>
            </Field>
            <Field label={t("notifications.quietTo")}>
              <Select
                value={String(preference.quiet_hours_end ?? 7)}
                onChange={(event) => update({ quiet_hours_end: Number(event.target.value) })}
              >
                {hours.map((hour) => (
                  <option key={hour} value={hour}>{`${String(hour).padStart(2, "0")}:00`}</option>
                ))}
              </Select>
            </Field>
          </div>
        )}
        <p className="text-xs text-ink-subtle">{t("notifications.quietHint")}</p>
      </fieldset>

      {error && <p className="text-sm text-danger">{error}</p>}
      {status && <p className="text-sm text-success">{status}</p>}
      <Button type="submit" disabled={saving}>
        {t("common.saveChanges")}
      </Button>
    </form>
  );
}
