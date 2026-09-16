import { useEffect, useState } from "react";
import type { DragEvent, FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { PencilIcon, TrashIcon } from "@heroicons/react/24/outline";
import { ArrowRightIcon } from "@heroicons/react/20/solid";

import { ErrorState } from "../components/ui/ErrorState";
import { Skeleton } from "../components/ui/Skeleton";
import { inventory, odometer, plans, vehicles } from "../lib/api";
import { ApiError } from "../lib/api/client";
import type { InventoryItem, Plan, PlanInput, PlanPriority, PlanStage, Vehicle, WorkKind } from "../lib/api/types";
import { useSession } from "../lib/session";

type PlanWithVehicle = Plan & { vehicleName: string; currentOdometer: number; distanceUnit: string };
type EditableStage = Exclude<PlanStage, "completed">;

const stages: PlanStage[] = ["planned", "in_progress", "testing", "completed"];
const editableStages: EditableStage[] = ["planned", "in_progress", "testing"];
const priorities: PlanPriority[] = ["low", "normal", "high", "urgent"];
const kinds: WorkKind[] = ["maintenance", "repair", "modification"];

const priorityStyles: Record<PlanPriority, string> = {
  low: "bg-slate-100 text-ink-muted dark:bg-slate-800 dark:text-slate-200",
  normal: "bg-blue-100 text-blue-800 dark:bg-blue-950/60 dark:text-blue-200",
  high: "bg-amber-100 text-amber-900 dark:bg-amber-950/60 dark:text-amber-200",
  urgent: "bg-red-100 text-red-900 dark:bg-red-950/60 dark:text-red-200",
};

export function Planner() {
  const { t, i18n } = useTranslation();
  const { me } = useSession();
  const [vehicleList, setVehicleList] = useState<Vehicle[] | null>(null);
  const [inventoryItems, setInventoryItems] = useState<InventoryItem[]>([]);
  const [items, setItems] = useState<PlanWithVehicle[] | null>(null);
  const [editing, setEditing] = useState<PlanWithVehicle | "new" | null>(null);
  const [completing, setCompleting] = useState<PlanWithVehicle | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const canWrite = me?.membership.role !== "reader";

  const load = () => {
    setError(null);
    Promise.all([vehicles.list(), inventory.list()])
      .then(async ([loadedVehicles, loadedInventory]) => {
        const groups = await Promise.all(
          loadedVehicles.map(async (vehicle) => {
            const [vehiclePlans, readings] = await Promise.all([
              plans.list(vehicle.id),
              odometer.list(vehicle.id),
            ]);
            const currentOdometer = readings.reduce((maximum, item) => Math.max(maximum, item.reading), 0);
            return vehiclePlans.map((plan) => ({
              ...plan,
              vehicleName: vehicle.name,
              currentOdometer,
              distanceUnit: vehicle.distance_unit,
            }));
          }),
        );
        setVehicleList(loadedVehicles);
        setInventoryItems(loadedInventory);
        setItems(groups.flat());
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

  const move = (plan: PlanWithVehicle, stage: EditableStage) => {
    if (plan.stage === stage || plan.stage === "completed") return;
    void act(() => plans.update(plan.vehicle_id, plan.id, { stage }));
  };

  const drop = (event: DragEvent<HTMLElement>, stage: PlanStage) => {
    event.preventDefault();
    if (stage === "completed") return;
    const plan = items?.find((item) => item.id === event.dataTransfer.getData("text/plain"));
    if (plan) move(plan, stage);
  };

  if (error) return <ErrorState onRetry={load} />;
  if (!vehicleList || !items) return <Skeleton lines={8} />;

  const currency = (value: string) =>
    Number(value).toLocaleString(i18n.language, { style: "currency", currency: "EUR" });
  const date = (value: string) =>
    new Intl.DateTimeFormat(i18n.language, { dateStyle: "medium" }).format(new Date(`${value}T12:00:00`));

  return (
    <div className="space-y-5">
      <div className="flex flex-col items-stretch gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-ink">{t("planner.title")}</h1>
          <p className="mt-1 text-sm text-ink-subtle">{t("planner.description")}</p>
        </div>
        {canWrite && (
          <button
            disabled={vehicleList.length === 0}
            onClick={() => {
              setCompleting(null);
              setEditing("new");
            }}
            className="self-start rounded-lg bg-copper px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-50"
          >
            {t("planner.add")}
          </button>
        )}
      </div>

      {editing && (
        <PlanForm
          key={editing === "new" ? "new" : editing.id}
          vehicles={vehicleList}
          initial={editing === "new" ? null : editing}
          onSaved={() => {
            setEditing(null);
            load();
          }}
          onCancel={() => setEditing(null)}
        />
      )}
      {completing && (
        <CompletePlanForm
          key={completing.id}
          plan={completing}
          inventoryItems={inventoryItems.filter((item) => !item.vehicle_id || item.vehicle_id === completing.vehicle_id)}
          onSaved={() => {
            setCompleting(null);
            load();
          }}
          onCancel={() => setCompleting(null)}
        />
      )}
      {actionError && <p role="alert" className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-800 dark:bg-red-950/40 dark:text-red-100">{actionError}</p>}

      {items.length === 0 ? (
        <div className="rounded-xl border border-dashed border-line-strong bg-raised p-8 text-center text-sm text-ink-subtle">
          {t("planner.empty")}
        </div>
      ) : (
        <div className="grid min-w-0 gap-4 md:grid-cols-2 xl:grid-cols-4">
          {stages.map((stage) => {
            const stageItems = items.filter((item) => item.stage === stage);
            return (
              <section
                key={stage}
                onDragOver={(event) => event.preventDefault()}
                onDrop={(event) => drop(event, stage)}
                className="min-w-0 rounded-xl bg-graphite/[0.035] p-3 dark:bg-white/[0.04]"
              >
                <div className="mb-3 flex items-center justify-between gap-2 px-1">
                  <h2 className="font-semibold text-ink">{t(`planner.stages.${stage}`)}</h2>
                  <span className="rounded-full bg-graphite/10 px-2 py-0.5 text-xs text-ink-muted dark:bg-white/10">{stageItems.length}</span>
                </div>
                <div className="space-y-3">
                  {stageItems.length === 0 && <p className="rounded-lg border border-dashed border-line p-4 text-center text-xs text-ink-subtle">{t("planner.emptyStage")}</p>}
                  {stageItems.map((plan) => (
                    <article
                      key={plan.id}
                      draggable={canWrite && plan.stage !== "completed"}
                      onDragStart={(event) => event.dataTransfer.setData("text/plain", plan.id)}
                      className="min-w-0 rounded-lg border border-line bg-raised p-4 shadow-sm"
                    >
                      <div className="flex min-w-0 items-start justify-between gap-2">
                        <span className={`rounded-full px-2 py-1 text-[11px] font-semibold uppercase ${priorityStyles[plan.priority]}`}>{t(`planner.priorities.${plan.priority}`)}</span>
                        <span className="shrink-0 text-xs text-ink-subtle">{t(`work.${plan.kind}`)}</span>
                      </div>
                      <h3 className="mt-3 break-words font-semibold text-ink">{plan.description}</h3>
                      <Link to={`/vehicles/${plan.vehicle_id}`} className="mt-1 block truncate text-sm text-copper hover:underline">{plan.vehicleName}</Link>
                      <div className="mt-3 space-y-1 text-xs text-graphite/55 dark:text-cream/55">
                        {plan.due_date && <p>{date(plan.due_date)}</p>}
                        {plan.due_odometer !== null && <p>{plan.due_odometer.toLocaleString(i18n.language)} {plan.distanceUnit}</p>}
                        {plan.estimated_cost !== null && <p>{currency(plan.estimated_cost)}</p>}
                      </div>
                      {plan.notes && <p className="mt-3 break-words text-sm text-graphite/65 dark:text-cream/65">{plan.notes}</p>}
                      {canWrite && plan.stage !== "completed" && (
                        <div className="mt-4 space-y-2 border-t border-graphite/5 pt-3 dark:border-white/5">
                          <select
                            aria-label={t("planner.stage")}
                            value={plan.stage}
                            onChange={(event) => move(plan, event.target.value as EditableStage)}
                            className="w-full rounded-md border border-line bg-raised px-2 py-2 text-sm"
                          >
                            {editableStages.map((option) => <option key={option} value={option}>{t(`planner.stages.${option}`)}</option>)}
                          </select>
                          <button onClick={() => { setEditing(null); setCompleting(plan); window.scrollTo({ top: 0, behavior: "smooth" }); }} className="w-full rounded-md bg-emerald-700 px-3 py-2 text-sm font-semibold text-white">{t("planner.complete")}</button>
                          <div className="flex items-center justify-between gap-3 text-sm">
                            <button onClick={() => { setCompleting(null); setEditing(plan); window.scrollTo({ top: 0, behavior: "smooth" }); }} className="flex items-center gap-1 font-medium text-copper"><PencilIcon aria-hidden="true" className="h-4 w-4" />{t("common.edit")}</button>
                            <button onClick={() => { if (window.confirm(t("common.confirmDelete"))) void act(() => plans.remove(plan.vehicle_id, plan.id)); }} className="flex items-center gap-1 font-medium text-danger"><TrashIcon aria-hidden="true" className="h-4 w-4" />{t("common.delete")}</button>
                          </div>
                        </div>
                      )}
                      {plan.stage === "completed" && plan.completed_work_record_id && (
                        <Link to={`/vehicles/${plan.vehicle_id}?section=work`} className="mt-4 flex items-center gap-1 border-t border-graphite/5 pt-3 text-sm font-medium text-copper dark:border-white/5">{t("planner.viewWork")}<ArrowRightIcon aria-hidden="true" className="h-3.5 w-3.5" /></Link>
                      )}
                    </article>
                  ))}
                </div>
              </section>
            );
          })}
        </div>
      )}
    </div>
  );
}

function PlanForm({ vehicles, initial, onSaved, onCancel }: { vehicles: Vehicle[]; initial: PlanWithVehicle | null; onSaved: () => void; onCancel: () => void }) {
  const { t } = useTranslation();
  const [vehicleId, setVehicleId] = useState(initial?.vehicle_id ?? vehicles[0]?.id ?? "");
  const [kind, setKind] = useState<WorkKind>(initial?.kind ?? "maintenance");
  const [priority, setPriority] = useState<PlanPriority>(initial?.priority ?? "normal");
  const [description, setDescription] = useState(initial?.description ?? "");
  const [estimatedCost, setEstimatedCost] = useState(initial?.estimated_cost ?? "");
  const [dueDate, setDueDate] = useState(initial?.due_date ?? "");
  const [dueOdometer, setDueOdometer] = useState(initial?.due_odometer?.toString() ?? "");
  const [notes, setNotes] = useState(initial?.notes ?? "");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    const payload: PlanInput = {
      kind,
      priority,
      description,
      estimated_cost: estimatedCost ? estimatedCost.replace(",", ".") : null,
      due_date: dueDate || null,
      due_odometer: dueOdometer ? Number(dueOdometer) : null,
      notes: notes || null,
    };
    try {
      if (initial) await plans.update(initial.vehicle_id, initial.id, payload);
      else await plans.create(vehicleId, payload);
      onSaved();
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : t("common.error"));
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={submit} className="grid min-w-0 gap-3 rounded-xl border border-line bg-raised p-4 shadow-sm sm:grid-cols-2">
      <select aria-label={t("nav.vehicle")} disabled={Boolean(initial)} value={vehicleId} onChange={(event) => setVehicleId(event.target.value)} className="rounded-lg border border-line px-3 py-2.5 disabled:opacity-60 bg-raised sm:col-span-2">{vehicles.map((vehicle) => <option key={vehicle.id} value={vehicle.id}>{vehicle.name}</option>)}</select>
      <label className="text-sm text-ink-muted">{t("planner.kind")}<select value={kind} onChange={(event) => setKind(event.target.value as WorkKind)} className="mt-1 w-full rounded-lg border border-line px-3 py-2.5 bg-raised">{kinds.map((value) => <option key={value} value={value}>{t(`work.${value}`)}</option>)}</select></label>
      <label className="text-sm text-ink-muted">{t("planner.priority")}<select value={priority} onChange={(event) => setPriority(event.target.value as PlanPriority)} className="mt-1 w-full rounded-lg border border-line px-3 py-2.5 bg-raised">{priorities.map((value) => <option key={value} value={value}>{t(`planner.priorities.${value}`)}</option>)}</select></label>
      <label className="text-sm text-ink-muted sm:col-span-2">{t("planner.descriptionLabel")}<input required value={description} onChange={(event) => setDescription(event.target.value)} className="mt-1 w-full rounded-lg border border-line px-3 py-2.5 bg-raised" /></label>
      <label className="text-sm text-ink-muted">{t("planner.estimatedCost")}<input inputMode="decimal" value={estimatedCost} onChange={(event) => setEstimatedCost(event.target.value)} className="mt-1 w-full rounded-lg border border-line px-3 py-2.5 bg-raised" /></label>
      <label className="text-sm text-ink-muted">{t("planner.dueDate")}<input type="date" value={dueDate} onChange={(event) => setDueDate(event.target.value)} className="mt-1 w-full rounded-lg border border-line px-3 py-2.5 bg-raised" /></label>
      <label className="text-sm text-ink-muted sm:col-span-2">{t("planner.dueOdometer")}<input type="number" min="0" inputMode="numeric" value={dueOdometer} onChange={(event) => setDueOdometer(event.target.value)} className="mt-1 w-full rounded-lg border border-line px-3 py-2.5 bg-raised" /></label>
      <label className="text-sm text-ink-muted sm:col-span-2">{t("planner.notes")}<textarea rows={3} value={notes} onChange={(event) => setNotes(event.target.value)} className="mt-1 w-full rounded-lg border border-line px-3 py-2.5 bg-raised" /></label>
      {error && <p role="alert" className="text-sm text-danger sm:col-span-2">{error}</p>}
      <div className="flex flex-col-reverse gap-2 sm:col-span-2 sm:flex-row sm:justify-end">
        <button type="button" onClick={onCancel} className="rounded-lg border border-line px-4 py-2.5 text-sm font-semibold">{t("common.cancel")}</button>
        <button disabled={saving} className="rounded-lg bg-copper px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-50">{initial ? t("common.saveChanges") : t("garage.save")}</button>
      </div>
    </form>
  );
}

function CompletePlanForm({ plan, inventoryItems, onSaved, onCancel }: { plan: PlanWithVehicle; inventoryItems: InventoryItem[]; onSaved: () => void; onCancel: () => void }) {
  const { t } = useTranslation();
  const [recordedOn, setRecordedOn] = useState(new Date().toISOString().slice(0, 10));
  const [odometerReading, setOdometerReading] = useState(plan.currentOdometer ? plan.currentOdometer.toString() : "");
  const [totalCost, setTotalCost] = useState(plan.estimated_cost ?? "");
  const [supplier, setSupplier] = useState("");
  const [notes, setNotes] = useState(plan.notes ?? "");
  const [inventoryItemId, setInventoryItemId] = useState("");
  const [inventoryQuantity, setInventoryQuantity] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    try {
      await plans.complete(plan.vehicle_id, plan.id, {
        recorded_on: recordedOn,
        odometer_reading: Number(odometerReading),
        total_cost: totalCost ? totalCost.replace(",", ".") : undefined,
        supplier: supplier || undefined,
        notes: notes || undefined,
        inventory_items: inventoryItemId && inventoryQuantity
          ? [{ item_id: inventoryItemId, quantity: inventoryQuantity.replace(",", ".") }]
          : undefined,
      });
      onSaved();
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : t("common.error"));
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={submit} className="grid min-w-0 gap-3 rounded-xl border border-emerald-500/30 bg-emerald-50 p-4 dark:bg-emerald-950/30 sm:grid-cols-2">
      <div className="sm:col-span-2"><h2 className="font-semibold text-ink">{t("planner.completeTitle")}</h2><p className="break-words text-sm text-ink-muted">{plan.description} · {plan.vehicleName}</p></div>
      <label className="text-sm text-ink-muted">{t("odometer.date")}<input required type="date" value={recordedOn} onChange={(event) => setRecordedOn(event.target.value)} className="mt-1 w-full rounded-lg border border-line px-3 py-2.5 bg-raised" /></label>
      <label className="text-sm text-ink-muted">{t("odometer.reading", { unit: plan.distanceUnit })}<input required type="number" min="0" inputMode="numeric" value={odometerReading} onChange={(event) => setOdometerReading(event.target.value)} className="mt-1 w-full rounded-lg border border-line px-3 py-2.5 bg-raised" /></label>
      <label className="text-sm text-ink-muted">{t("work.cost")}<input inputMode="decimal" value={totalCost} onChange={(event) => setTotalCost(event.target.value)} className="mt-1 w-full rounded-lg border border-line px-3 py-2.5 bg-raised" /></label>
      <label className="text-sm text-ink-muted">{t("expenses.supplier")}<input value={supplier} onChange={(event) => setSupplier(event.target.value)} className="mt-1 w-full rounded-lg border border-line px-3 py-2.5 bg-raised" /></label>
      <label className="text-sm text-ink-muted sm:col-span-2">{t("planner.notes")}<textarea rows={3} value={notes} onChange={(event) => setNotes(event.target.value)} className="mt-1 w-full rounded-lg border border-line px-3 py-2.5 bg-raised" /></label>
      {inventoryItems.length > 0 && <><label className="text-sm text-ink-muted">{t("planner.inventoryItem")}<select value={inventoryItemId} onChange={(event) => setInventoryItemId(event.target.value)} className="mt-1 w-full rounded-lg border border-line px-3 py-2.5 bg-raised"><option value="">{t("planner.noInventory")}</option>{inventoryItems.map((item) => <option key={item.id} value={item.id}>{item.name} ({Number(item.quantity).toLocaleString()} {item.unit})</option>)}</select></label><label className="text-sm text-ink-muted">{t("inventory.quantity")}<input inputMode="decimal" value={inventoryQuantity} onChange={(event) => setInventoryQuantity(event.target.value)} disabled={!inventoryItemId} className="mt-1 w-full rounded-lg border border-line px-3 py-2.5 disabled:opacity-50 bg-raised" /></label></>}
      {error && <p role="alert" className="text-sm text-danger sm:col-span-2">{error}</p>}
      <div className="flex flex-col-reverse gap-2 sm:col-span-2 sm:flex-row sm:justify-end">
        <button type="button" onClick={onCancel} className="rounded-lg border border-line px-4 py-2.5 text-sm font-semibold">{t("common.cancel")}</button>
        <button disabled={saving || !odometerReading} className="rounded-lg bg-emerald-700 px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-50">{t("planner.createWork")}</button>
      </div>
    </form>
  );
}
