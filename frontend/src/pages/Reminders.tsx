import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { ErrorState } from "../components/ui/ErrorState";
import { Skeleton } from "../components/ui/Skeleton";
import { reminders, vehicles } from "../lib/api";
import { ApiError } from "../lib/api/client";
import type { Reminder, Vehicle } from "../lib/api/types";

type ReminderWithVehicle = Reminder & { vehicleName: string };

const urgencyStyles = {
  overdue: "border-red-500 bg-red-50 text-red-800",
  very_urgent: "border-orange-500 bg-orange-50 text-orange-800",
  urgent: "border-amber-500 bg-amber-50 text-amber-800",
  upcoming: "border-blue-400 bg-blue-50 text-blue-800",
  future: "border-slate-300 bg-white text-slate-700",
  completed: "border-emerald-400 bg-emerald-50 text-emerald-800",
};

export function Reminders() {
  const { t } = useTranslation();
  const [vehicleList, setVehicleList] = useState<Vehicle[] | null>(null);
  const [items, setItems] = useState<ReminderWithVehicle[] | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [showForm, setShowForm] = useState(false);
  const load = () => {
    setError(null);
    vehicles.list().then(async (loadedVehicles) => {
      const groups = await Promise.all(loadedVehicles.map(async (vehicle) =>
        (await reminders.list(vehicle.id)).map((item) => ({ ...item, vehicleName: vehicle.name }))
      ));
      setVehicleList(loadedVehicles); setItems(groups.flat());
    }).catch(setError);
  };
  useEffect(load, []);
  if (error) return <ErrorState onRetry={load} />;
  if (!vehicleList || !items) return <Skeleton lines={7} />;
  return <div className="space-y-6"><div className="flex items-end justify-between gap-4"><div><h1 className="text-2xl font-bold text-slate-900">{t("reminders.title")}</h1><p className="mt-1 text-sm text-slate-500">{t("reminders.description")}</p></div><button disabled={!vehicleList.length} onClick={() => setShowForm((value) => !value)} className="rounded-lg bg-[#B94A22] px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-50">{t("reminders.add")}</button></div>
    {showForm && <ReminderForm vehicleList={vehicleList} onCreated={() => { setShowForm(false); load(); }} />}
    {items.length === 0 ? <div className="rounded-xl border border-dashed border-slate-300 bg-white p-8 text-center text-sm text-slate-500">{t("reminders.empty")}</div> : <div className="grid gap-3 lg:grid-cols-2">{items.map((item) => <article key={item.id} className={`rounded-xl border-l-4 p-4 shadow-sm ${urgencyStyles[item.urgency]}`}><div className="flex justify-between gap-4"><div><p className="font-semibold">{item.title}</p><Link to={`/vehicles/${item.vehicle_id}`} className="text-xs opacity-75">{item.vehicleName}</Link></div><span className="text-xs font-semibold uppercase">{t(`reminders.${item.urgency}`)}</span></div><p className="mt-3 text-sm">{[item.due_date, item.due_odometer ? `${item.due_odometer.toLocaleString()} km` : null].filter(Boolean).join(" · ")}</p>{item.status !== "completed" && <button onClick={() => void reminders.complete(item.vehicle_id, item.id).then(load)} className="mt-3 text-sm font-semibold underline">{t("reminders.complete")}</button>}</article>)}</div>}
  </div>;
}

function ReminderForm({ vehicleList, onCreated }: { vehicleList: Vehicle[]; onCreated: () => void }) {
  const { t } = useTranslation();
  const [vehicleId, setVehicleId] = useState(vehicleList[0]?.id ?? "");
  const [title, setTitle] = useState("");
  const [dueDate, setDueDate] = useState("");
  const [dueOdometer, setDueOdometer] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  async function submit(event: FormEvent) {
    event.preventDefault(); setSaving(true); setError(null);
    try { await reminders.create(vehicleId, { title, due_date: dueDate || undefined, due_odometer: dueOdometer ? Number(dueOdometer) : undefined }); onCreated(); }
    catch (cause) { setError(cause instanceof ApiError ? cause.message : t("common.error")); }
    finally { setSaving(false); }
  }
  return <form onSubmit={submit} className="grid gap-3 rounded-xl border border-slate-200 bg-white p-4 sm:grid-cols-2"><select value={vehicleId} onChange={(event) => setVehicleId(event.target.value)} className="rounded-lg border border-slate-300 px-3 py-2.5">{vehicleList.map((vehicle) => <option key={vehicle.id} value={vehicle.id}>{vehicle.name}</option>)}</select><input required placeholder={t("reminders.name")} value={title} onChange={(event) => setTitle(event.target.value)} className="rounded-lg border border-slate-300 px-3 py-2.5" /><label className="text-sm text-slate-600">{t("reminders.dueDate")}<input type="date" value={dueDate} onChange={(event) => setDueDate(event.target.value)} className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2.5" /></label><label className="text-sm text-slate-600">{t("reminders.dueOdometer")}<input type="number" inputMode="numeric" value={dueOdometer} onChange={(event) => setDueOdometer(event.target.value)} className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2.5" /></label>{error && <p className="text-sm text-red-700 sm:col-span-2">{error}</p>}<button disabled={saving || (!dueDate && !dueOdometer)} className="rounded-lg bg-[#B94A22] px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-50 sm:col-span-2">{t("garage.save")}</button></form>;
}
