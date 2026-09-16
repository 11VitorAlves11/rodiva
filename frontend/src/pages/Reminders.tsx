import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { ErrorState } from "../components/ui/ErrorState";
import { Skeleton } from "../components/ui/Skeleton";
import { reminders, vehicles } from "../lib/api";
import { ApiError } from "../lib/api/client";
import type { Reminder, ReminderUpdateInput, Vehicle } from "../lib/api/types";
import { useSession } from "../lib/session";

type ReminderWithVehicle = Reminder & { vehicleName: string };

// Urgency carries its own colour and never borrows brand copper (RF-IDV-003).
// The top two steps share the danger hue and separate by weight instead, so the
// ramp needs no orange — which would read as the brand mark in the dark theme.
const urgencyStyles = {
  overdue: "border-danger-solid bg-danger-solid text-white",
  very_urgent: "border-danger bg-danger-soft text-danger",
  urgent: "border-warning bg-warning-soft text-warning",
  upcoming: "border-info bg-info-soft text-info",
  future: "border-line-strong bg-raised text-ink",
  completed: "border-success bg-success-soft text-success",
};

const urgencyOrder = {
  overdue: 0,
  very_urgent: 1,
  urgent: 2,
  upcoming: 3,
  future: 4,
  completed: 5,
};

export function Reminders() {
  const { t, i18n } = useTranslation();
  const { me } = useSession();
  const [vehicleList, setVehicleList] = useState<Vehicle[] | null>(null);
  const [items, setItems] = useState<ReminderWithVehicle[] | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<ReminderWithVehicle | null>(null);
  const canWrite = me?.membership.role !== "reader";

  const load = () => {
    setError(null);
    vehicles
      .list()
      .then(async (loadedVehicles) => {
        const groups = await Promise.all(
          loadedVehicles.map(async (vehicle) =>
            (await reminders.list(vehicle.id)).map((item) => ({ ...item, vehicleName: vehicle.name })),
          ),
        );
        setVehicleList(loadedVehicles);
        setItems(groups.flat().sort((a, b) => urgencyOrder[a.urgency] - urgencyOrder[b.urgency]));
      })
      .catch(setError);
  };

  useEffect(load, []);

  const act = async (operation: () => Promise<unknown>) => {
    setActionError(null);
    try {
      await operation();
      load();
    } catch (cause) {
      setActionError(cause instanceof ApiError ? cause.message : t("common.error"));
    }
  };

  if (error) return <ErrorState onRetry={load} />;
  if (!vehicleList || !items) return <Skeleton lines={7} />;

  const repeatSummary = (item: Reminder) => {
    const parts = [];
    if (item.repeat_days) parts.push(t("reminders.repeatsEveryDays", { count: item.repeat_days }));
    if (item.repeat_distance) parts.push(t("reminders.repeatsEveryDistance", { count: item.repeat_distance }));
    return parts.join(" · ");
  };

  const formatDate = (value: string) =>
    new Intl.DateTimeFormat(i18n.language, { dateStyle: "medium" }).format(new Date(`${value}T12:00:00`));

  return (
    <div className="space-y-6">
      <div className="flex flex-col items-stretch gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-ink">{t("reminders.title")}</h1>
          <p className="mt-1 text-sm text-ink-subtle">{t("reminders.description")}</p>
        </div>
        {canWrite && (
          <button
            disabled={!vehicleList.length}
            onClick={() => {
              setEditing(null);
              setShowForm((value) => !value);
            }}
            className="self-start rounded-lg bg-copper px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-50"
          >
            {t("reminders.add")}
          </button>
        )}
      </div>

      {(showForm || editing) && (
        <ReminderForm
          key={editing?.id ?? "new"}
          vehicleList={vehicleList}
          initial={editing}
          onSaved={() => {
            setShowForm(false);
            setEditing(null);
            load();
          }}
          onCancel={() => {
            setShowForm(false);
            setEditing(null);
          }}
        />
      )}

      {actionError && <p role="alert" className="rounded-lg bg-danger-soft px-4 py-3 text-sm text-danger">{actionError}</p>}

      {items.length === 0 ? (
        <div className="rounded-xl border border-dashed border-line-strong bg-raised p-8 text-center text-sm text-ink-subtle">
          {t("reminders.empty")}
        </div>
      ) : (
        <div className="grid gap-3 lg:grid-cols-2">
          {items.map((item) => (
            <article key={item.id} className={`rounded-xl border border-l-4 p-4 shadow-sm ${urgencyStyles[item.urgency]}`}>
              <div className="flex justify-between gap-4">
                <div className="min-w-0">
                  <p className="truncate font-semibold">{item.title}</p>
                  <Link to={`/vehicles/${item.vehicle_id}`} className="text-xs opacity-75 hover:underline">{item.vehicleName}</Link>
                </div>
                <span className="shrink-0 text-xs font-semibold uppercase">{t(`reminders.${item.urgency}`)}</span>
              </div>
              <p className="mt-3 text-sm">
                {[
                  item.due_date ? formatDate(item.due_date) : null,
                  item.due_odometer !== null ? `${item.due_odometer.toLocaleString(i18n.language)} km` : null,
                ].filter(Boolean).join(" · ")}
              </p>
              {repeatSummary(item) && <p className="mt-1 text-xs opacity-75">{repeatSummary(item)}</p>}
              {item.notes && <p className="mt-3 whitespace-pre-wrap text-sm opacity-80">{item.notes}</p>}
              {canWrite && (
                <div className="mt-4 flex flex-wrap gap-x-4 gap-y-2 border-t border-current/10 pt-3 text-sm font-semibold">
                  {item.status === "completed" ? (
                    <button onClick={() => void act(() => reminders.reopen(item.vehicle_id, item.id))} className="underline-offset-4 hover:underline">
                      {t("reminders.reopen")}
                    </button>
                  ) : (
                    <button onClick={() => void act(() => reminders.complete(item.vehicle_id, item.id))} className="underline-offset-4 hover:underline">
                      {t("reminders.complete")}
                    </button>
                  )}
                  <button
                    onClick={() => {
                      setShowForm(false);
                      setEditing(item);
                      window.scrollTo({ top: 0, behavior: "smooth" });
                    }}
                    className="underline-offset-4 hover:underline"
                  >
                    {t("reminders.edit")}
                  </button>
                  <button
                    onClick={() => {
                      if (window.confirm(t("common.confirmDelete"))) {
                        void act(() => reminders.remove(item.vehicle_id, item.id));
                      }
                    }}
                    // Inherits the card's colour like the other actions: forcing
                    // the danger tint puts salmon on the solid overdue red.
                    className="ml-auto underline-offset-4 hover:underline"
                  >
                    {t("common.delete")}
                  </button>
                </div>
              )}
            </article>
          ))}
        </div>
      )}
    </div>
  );
}

function ReminderForm({
  vehicleList,
  initial,
  onSaved,
  onCancel,
}: {
  vehicleList: Vehicle[];
  initial: ReminderWithVehicle | null;
  onSaved: () => void;
  onCancel: () => void;
}) {
  const { t } = useTranslation();
  const [vehicleId, setVehicleId] = useState(initial?.vehicle_id ?? vehicleList[0]?.id ?? "");
  const [title, setTitle] = useState(initial?.title ?? "");
  const [dueDate, setDueDate] = useState(initial?.due_date ?? "");
  const [dueOdometer, setDueOdometer] = useState(initial?.due_odometer?.toString() ?? "");
  const [repeatDays, setRepeatDays] = useState(initial?.repeat_days?.toString() ?? "");
  const [repeatDistance, setRepeatDistance] = useState(initial?.repeat_distance?.toString() ?? "");
  const [notes, setNotes] = useState(initial?.notes ?? "");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    const payload: ReminderUpdateInput = {
      title,
      due_date: dueDate || null,
      due_odometer: dueOdometer ? Number(dueOdometer) : null,
      repeat_days: repeatDays ? Number(repeatDays) : null,
      repeat_distance: repeatDistance ? Number(repeatDistance) : null,
      notes: notes || null,
    };
    try {
      if (initial) await reminders.update(initial.vehicle_id, initial.id, payload);
      else {
        await reminders.create(vehicleId, {
          title,
          due_date: dueDate || undefined,
          due_odometer: dueOdometer ? Number(dueOdometer) : undefined,
          repeat_days: repeatDays ? Number(repeatDays) : undefined,
          repeat_distance: repeatDistance ? Number(repeatDistance) : undefined,
          notes: notes || undefined,
        });
      }
      onSaved();
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : t("common.error"));
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={submit} className="grid gap-3 rounded-xl border border-line bg-raised p-4 sm:grid-cols-2">
      <select
        value={vehicleId}
        onChange={(event) => setVehicleId(event.target.value)}
        disabled={Boolean(initial)}
        aria-label={t("nav.vehicle")}
        className="rounded-lg border border-line px-3 py-2.5 disabled:opacity-60 bg-raised sm:col-span-2"
      >
        {vehicleList.map((vehicle) => <option key={vehicle.id} value={vehicle.id}>{vehicle.name}</option>)}
      </select>
      <input required placeholder={t("reminders.name")} value={title} onChange={(event) => setTitle(event.target.value)} className="rounded-lg border border-line px-3 py-2.5 bg-raised sm:col-span-2" />
      <label className="text-sm text-ink-muted">{t("reminders.dueDate")}<input type="date" value={dueDate} onChange={(event) => setDueDate(event.target.value)} className="mt-1 w-full rounded-lg border border-line px-3 py-2.5 bg-raised" /></label>
      <label className="text-sm text-ink-muted">{t("reminders.dueOdometer")}<input type="number" inputMode="numeric" min="0" value={dueOdometer} onChange={(event) => setDueOdometer(event.target.value)} className="mt-1 w-full rounded-lg border border-line px-3 py-2.5 bg-raised" /></label>
      <label className="text-sm text-ink-muted">{t("reminders.repeatDays")}<input type="number" inputMode="numeric" min="1" value={repeatDays} onChange={(event) => setRepeatDays(event.target.value)} className="mt-1 w-full rounded-lg border border-line px-3 py-2.5 bg-raised" /></label>
      <label className="text-sm text-ink-muted">{t("reminders.repeatDistance")}<input type="number" inputMode="numeric" min="1" value={repeatDistance} onChange={(event) => setRepeatDistance(event.target.value)} className="mt-1 w-full rounded-lg border border-line px-3 py-2.5 bg-raised" /></label>
      <label className="text-sm text-ink-muted sm:col-span-2">{t("reminders.notes")}<textarea rows={3} value={notes} onChange={(event) => setNotes(event.target.value)} className="mt-1 w-full rounded-lg border border-line px-3 py-2.5 bg-raised" /></label>
      {error && <p role="alert" className="text-sm text-danger sm:col-span-2">{error}</p>}
      <div className="flex justify-end gap-3 sm:col-span-2">
        <button type="button" onClick={onCancel} className="rounded-lg border border-line px-4 py-2.5 text-sm font-semibold">{t("common.cancel")}</button>
        <button disabled={saving || (!dueDate && !dueOdometer)} className="rounded-lg bg-copper px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-50">{initial ? t("reminders.update") : t("garage.save")}</button>
      </div>
    </form>
  );
}
