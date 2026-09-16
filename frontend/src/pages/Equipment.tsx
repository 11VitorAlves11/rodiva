import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { TrashIcon } from "@heroicons/react/24/outline";

import { ErrorState } from "../components/ui/ErrorState";
import { Skeleton } from "../components/ui/Skeleton";
import { equipment, odometer, vehicles } from "../lib/api";
import { ApiError } from "../lib/api/client";
import type { Equipment as EquipmentType, EquipmentKind, Reminder, Vehicle } from "../lib/api/types";
import { useSession } from "../lib/session";

type Item = EquipmentType & { vehicleName: string; unit: string; current: number };
type Action = { item: Item; kind: "mount" | "unmount" | "rotate" };

export function Equipment() {
  const { t, i18n } = useTranslation(); const { me } = useSession();
  const [items, setItems] = useState<Item[] | null>(null); const [vehicleList, setVehicleList] = useState<Vehicle[]>([]);
  const [creating, setCreating] = useState(false); const [action, setAction] = useState<Action | null>(null); const [error, setError] = useState<Error | null>(null);
  const [remindersFor, setRemindersFor] = useState<string | null>(null);
  const canWrite = me?.membership.role !== "reader";
  const load = () => { setError(null); vehicles.list().then(async (list) => { setVehicleList(list); const groups = await Promise.all(list.map(async (vehicle) => { const [records, readings] = await Promise.all([equipment.list(vehicle.id), odometer.list(vehicle.id)]); const current = readings.reduce((max, reading) => Math.max(max, reading.reading), 0); return records.map((item) => ({ ...item, vehicleName: vehicle.name, unit: vehicle.distance_unit, current })); })); setItems(groups.flat()); }).catch(setError); };
  useEffect(load, []);
  if (error) return <ErrorState onRetry={load} />; if (!items) return <Skeleton lines={7} />;
  return <div className="min-w-0 space-y-5"><div className="flex flex-col items-stretch gap-3 sm:flex-row sm:items-end sm:justify-between"><div><h1 className="text-2xl font-bold text-ink">{t("equipment.title")}</h1><p className="mt-1 text-sm text-ink-subtle">{t("equipment.description")}</p></div>{canWrite && <button onClick={() => setCreating(!creating)} className="self-start rounded-lg bg-copper px-4 py-2.5 text-sm font-semibold text-white">{t("equipment.add")}</button>}</div>
    {creating && <EquipmentForm vehicles={vehicleList} onSaved={() => { setCreating(false); load(); }} />}{action && <EquipmentAction action={action} onCancel={() => setAction(null)} onSaved={() => { setAction(null); load(); }} />}
    {items.length === 0 ? <p className="rounded-xl border border-dashed border-line-strong bg-raised p-8 text-center text-sm text-graphite/50">{t("equipment.empty")}</p> : <div className="grid min-w-0 gap-3 sm:grid-cols-2 xl:grid-cols-3">{items.map((item) => <article key={item.id} className="min-w-0 rounded-xl border border-line bg-raised p-4 shadow-sm"><div className="flex min-w-0 justify-between gap-2"><div className="min-w-0"><h2 className="break-words font-semibold text-ink">{item.name}</h2><p className="truncate text-xs text-ink-subtle">{item.vehicleName} · {t(`equipment.kinds.${item.kind}`)}</p></div><span className={`shrink-0 rounded-full px-2 py-1 text-[10px] font-bold uppercase ${item.status === "mounted" ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-200" : "bg-sunken text-ink-muted dark:bg-slate-800 dark:text-slate-200"}`}>{t(`equipment.statuses.${item.status}`)}</span></div>{item.kind === "tires" && <p className="mt-3 text-sm text-ink-muted">{[item.manufacturer, item.model, item.tire_size, item.tire_dot ? `DOT ${item.tire_dot}` : null].filter(Boolean).join(" · ")}</p>}<p className="mt-3 text-lg font-bold text-ink">{item.distance_accumulated.toLocaleString(i18n.language)} <span className="text-sm font-medium opacity-50">{item.unit}</span></p><p className="text-xs text-ink-subtle">{t("equipment.distance")}</p>
      <button onClick={() => setRemindersFor(remindersFor === item.id ? null : item.id)} className="mt-2 text-xs font-semibold text-copper underline-offset-4 hover:underline">{t("equipment.reminders.label")}{item.open_reminders_count > 0 ? ` (${item.open_reminders_count})` : ""}</button>
      {remindersFor === item.id && <EquipmentReminders item={item} canWrite={canWrite} onCountChanged={load} />}
      {canWrite && <div className="mt-4 flex flex-wrap gap-2 border-t border-graphite/5 pt-3 dark:border-white/5">{item.status === "mounted" ? <><button onClick={() => setAction({ item, kind: "unmount" })} className="rounded-md border border-line px-3 py-2 text-sm font-semibold">{t("equipment.unmount")}</button>{item.kind === "tires" && <button onClick={() => setAction({ item, kind: "rotate" })} className="rounded-md border border-line px-3 py-2 text-sm font-semibold">{t("equipment.rotate")}</button>}</> : !["sold", "discarded"].includes(item.status) && <button onClick={() => setAction({ item, kind: "mount" })} className="rounded-md bg-copper px-3 py-2 text-sm font-semibold text-white">{t("equipment.mount")}</button>}<button onClick={() => { if (window.confirm(t("common.confirmDelete"))) void equipment.remove(item.vehicle_id, item.id).then(load); }} className="ml-auto flex items-center gap-1 px-2 text-sm font-semibold text-danger"><TrashIcon aria-hidden="true" className="h-4 w-4" />{t("common.delete")}</button></div>}</article>)}</div>}</div>;
}

function EquipmentForm({ vehicles, onSaved }: { vehicles: Vehicle[]; onSaved: () => void }) {
  const { t } = useTranslation(); const [vehicleId, setVehicleId] = useState(vehicles[0]?.id ?? ""); const [name, setName] = useState(""); const [kind, setKind] = useState<EquipmentKind>("tires"); const [manufacturer, setManufacturer] = useState(""); const [model, setModel] = useState(""); const [size, setSize] = useState(""); const [dot, setDot] = useState(""); const [error, setError] = useState<string | null>(null);
  async function submit(event: FormEvent) { event.preventDefault(); try { await equipment.create(vehicleId, { name, kind, manufacturer: manufacturer || undefined, model: model || undefined, tire_size: size || undefined, tire_dot: dot || undefined }); onSaved(); } catch (cause) { setError(cause instanceof ApiError ? cause.message : t("common.error")); } }
  return <form onSubmit={submit} className="grid min-w-0 gap-3 rounded-xl border border-line bg-raised p-4 sm:grid-cols-2"><select aria-label={t("nav.vehicle")} value={vehicleId} onChange={(e) => setVehicleId(e.target.value)} className="rounded-lg border px-3 py-2.5 bg-raised sm:col-span-2">{vehicles.map((v) => <option key={v.id} value={v.id}>{v.name}</option>)}</select><label className="text-sm">{t("equipment.name")}<input required value={name} onChange={(e) => setName(e.target.value)} className="mt-1 rounded-lg border px-3 py-2.5 bg-raised" /></label><label className="text-sm">{t("equipment.kind")}<select value={kind} onChange={(e) => setKind(e.target.value as EquipmentKind)} className="mt-1 rounded-lg border px-3 py-2.5 bg-raised">{(["tires", "trailer", "roof_rack", "accessory", "other"] as EquipmentKind[]).map((v) => <option key={v} value={v}>{t(`equipment.kinds.${v}`)}</option>)}</select></label><input placeholder={t("equipment.manufacturer")} value={manufacturer} onChange={(e) => setManufacturer(e.target.value)} className="rounded-lg border px-3 py-2.5 bg-raised" /><input placeholder={t("equipment.model")} value={model} onChange={(e) => setModel(e.target.value)} className="rounded-lg border px-3 py-2.5 bg-raised" />{kind === "tires" && <><input placeholder={t("equipment.size")} value={size} onChange={(e) => setSize(e.target.value)} className="rounded-lg border px-3 py-2.5 bg-raised" /><input placeholder="DOT" value={dot} onChange={(e) => setDot(e.target.value)} className="rounded-lg border px-3 py-2.5 bg-raised" /></>}{error && <p className="text-sm text-danger sm:col-span-2">{error}</p>}<button className="rounded-lg bg-copper px-4 py-2.5 font-semibold text-white sm:col-span-2">{t("garage.save")}</button></form>;
}

function EquipmentAction({ action, onCancel, onSaved }: { action: Action; onCancel: () => void; onSaved: () => void }) {
  const { t } = useTranslation(); const [on, setOn] = useState(new Date().toISOString().slice(0, 10)); const [odo, setOdo] = useState(action.item.current.toString()); const [positions, setPositions] = useState(["A", "B", "C", "D"]); const [error, setError] = useState<string | null>(null);
  async function submit(event: FormEvent) { event.preventDefault(); const body = { on, odometer: Number(odo), positions: action.kind === "unmount" ? undefined : { front_left: positions[0], front_right: positions[1], rear_left: positions[2], rear_right: positions[3] } }; try { await equipment[action.kind](action.item.vehicle_id, action.item.id, body); onSaved(); } catch (cause) { setError(cause instanceof ApiError ? cause.message : t("common.error")); } }
  return <form onSubmit={submit} className="grid gap-3 rounded-xl border border-copper/20 bg-raised p-4 sm:grid-cols-2"><h2 className="font-semibold sm:col-span-2">{t(`equipment.${action.kind}`)} · {action.item.name}</h2><input required type="date" value={on} onChange={(e) => setOn(e.target.value)} className="rounded-lg border px-3 py-2.5 bg-raised" /><input required type="number" inputMode="numeric" value={odo} onChange={(e) => setOdo(e.target.value)} className="rounded-lg border px-3 py-2.5 bg-raised" />{action.kind !== "unmount" && positions.map((value, index) => <input key={index} aria-label={t(`equipment.positions.${index}`)} value={value} onChange={(e) => setPositions((current) => current.map((entry, i) => i === index ? e.target.value : entry))} className="rounded-lg border px-3 py-2.5 bg-raised" />)}{error && <p className="text-sm text-danger sm:col-span-2">{error}</p>}<div className="flex flex-col-reverse gap-2 sm:col-span-2 sm:flex-row sm:justify-end"><button type="button" onClick={onCancel} className="rounded-lg border px-4 py-2.5">{t("common.cancel")}</button><button className="rounded-lg bg-copper px-4 py-2.5 font-semibold text-white">{t("garage.save")}</button></div></form>;
}

function EquipmentReminders({
  item,
  canWrite,
  onCountChanged,
}: {
  item: Item;
  canWrite: boolean;
  onCountChanged: () => void;
}) {
  const { t, i18n } = useTranslation();
  const [list, setList] = useState<Reminder[] | null>(null);
  const [creating, setCreating] = useState(false);
  const [title, setTitle] = useState("");
  const [dueDate, setDueDate] = useState("");
  const [dueOdometer, setDueOdometer] = useState("");
  const [error, setError] = useState<string | null>(null);

  const load = () => {
    equipment.reminders(item.vehicle_id, item.id).then(setList).catch(() => setList([]));
  };
  useEffect(load, [item.id, item.vehicle_id]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      await equipment.createReminder(item.vehicle_id, item.id, {
        title,
        due_date: dueDate || undefined,
        due_odometer: dueOdometer ? Number(dueOdometer) : undefined,
      });
      setTitle("");
      setDueDate("");
      setDueOdometer("");
      setCreating(false);
      load();
      onCountChanged();
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : t("common.error"));
    }
  }

  return (
    <div className="mt-3 rounded-lg border border-line bg-cream/40 p-3 dark:bg-surface-dark">
      <div className="flex items-center justify-between">
        <h3 className="text-xs font-semibold uppercase text-ink-muted">{t("equipment.reminders.label")}</h3>
        {canWrite && (
          <button onClick={() => setCreating((value) => !value)} className="text-xs font-semibold text-copper">
            {t("equipment.reminders.add")}
          </button>
        )}
      </div>
      {!list ? null : list.length === 0 ? (
        <p className="mt-2 text-xs text-ink-subtle">{t("equipment.reminders.empty")}</p>
      ) : (
        <ul className="mt-2 space-y-1">
          {list.map((reminder) => (
            <li key={reminder.id} className="flex items-center justify-between gap-2 text-xs">
              <span className="truncate">{reminder.title}</span>
              <span className="shrink-0 opacity-60">
                {[reminder.due_date, reminder.due_odometer !== null ? `${reminder.due_odometer.toLocaleString(i18n.language)} ${item.unit}` : null]
                  .filter(Boolean)
                  .join(" · ")}
              </span>
            </li>
          ))}
        </ul>
      )}
      {creating && (
        <form onSubmit={submit} className="mt-3 grid gap-2 border-t border-line pt-3">
          <input required placeholder={t("reminders.name")} value={title} onChange={(e) => setTitle(e.target.value)} className="rounded-lg border border-line px-3 py-2 text-sm dark:bg-surface-dark-raised" />
          <div className="grid grid-cols-2 gap-2">
            <input type="date" aria-label={t("reminders.dueDate")} value={dueDate} onChange={(e) => setDueDate(e.target.value)} className="rounded-lg border border-line px-3 py-2 text-sm dark:bg-surface-dark-raised" />
            <input type="number" inputMode="numeric" min="0" placeholder={t("reminders.dueOdometer")} value={dueOdometer} onChange={(e) => setDueOdometer(e.target.value)} className="rounded-lg border border-line px-3 py-2 text-sm dark:bg-surface-dark-raised" />
          </div>
          {error && <p className="text-xs text-danger">{error}</p>}
          <button disabled={!dueDate && !dueOdometer} className="justify-self-end rounded-lg bg-copper px-3 py-2 text-xs font-semibold text-white disabled:opacity-50">
            {t("garage.save")}
          </button>
        </form>
      )}
    </div>
  );
}
