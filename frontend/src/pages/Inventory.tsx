import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { XMarkIcon } from "@heroicons/react/24/outline";

import { ErrorState } from "../components/ui/ErrorState";
import { Skeleton } from "../components/ui/Skeleton";
import { inventory, vehicles } from "../lib/api";
import { ApiError } from "../lib/api/client";
import type { InventoryItem, MovementKind, StockMovement, Vehicle } from "../lib/api/types";
import { useSession } from "../lib/session";

const movementKinds: MovementKind[] = ["entry", "requisition", "return", "removal", "adjustment"];

export function Inventory() {
  const { t, i18n } = useTranslation();
  const { me } = useSession();
  const [items, setItems] = useState<InventoryItem[] | null>(null);
  const [vehicleList, setVehicleList] = useState<Vehicle[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [selected, setSelected] = useState<InventoryItem | null>(null);
  const [movements, setMovements] = useState<StockMovement[] | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const canWrite = me?.membership.role !== "reader";

  const load = () => {
    setError(null);
    Promise.all([inventory.list(), vehicles.list()])
      .then(([loadedItems, loadedVehicles]) => {
        setItems(loadedItems);
        setVehicleList(loadedVehicles);
        setSelected((current) =>
          current ? loadedItems.find((item) => item.id === current.id) ?? null : null,
        );
      })
      .catch(setError);
  };

  useEffect(load, []);

  const openMovements = async (item: InventoryItem) => {
    setSelected(item);
    setMovements(null);
    try {
      setMovements(await inventory.movements(item.id));
    } catch (cause) {
      setError(cause instanceof Error ? cause : new Error(t("common.error")));
    }
  };

  if (error) return <ErrorState onRetry={load} />;
  if (!items) return <Skeleton lines={7} />;

  const vehicleName = (id: string | null) =>
    id ? vehicleList.find((vehicle) => vehicle.id === id)?.name ?? "—" : t("inventory.shared");

  return (
    <div className="min-w-0 space-y-5">
      <div className="flex flex-col items-stretch gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div><h1 className="text-2xl font-bold text-graphite dark:text-cream">{t("inventory.title")}</h1><p className="mt-1 text-sm text-graphite/50 dark:text-cream/50">{t("inventory.description")}</p></div>
        {canWrite && <button onClick={() => setShowForm((value) => !value)} className="self-start rounded-lg bg-copper px-4 py-2.5 text-sm font-semibold text-white">{t("inventory.add")}</button>}
      </div>
      {showForm && <ItemForm vehicles={vehicleList} onSaved={() => { setShowForm(false); load(); }} />}
      {items.length === 0 ? <p className="rounded-xl border border-dashed border-graphite/20 bg-white p-8 text-center text-sm text-graphite/50 dark:border-white/20 dark:bg-surface-dark-raised dark:text-cream/50">{t("inventory.empty")}</p> : (
        <div className="grid min-w-0 gap-3 sm:grid-cols-2 xl:grid-cols-3">{items.map((item) => (
          <article key={item.id} className={`min-w-0 rounded-xl border bg-white p-4 shadow-sm dark:bg-surface-dark-raised ${item.low_stock ? "border-amber-400 dark:border-amber-700" : "border-graphite/10 dark:border-white/10"}`}>
            <div className="flex min-w-0 items-start justify-between gap-3"><div className="min-w-0"><h2 className="break-words font-semibold text-graphite dark:text-cream">{item.name}</h2><p className="truncate text-xs text-graphite/50 dark:text-cream/50">{[item.manufacturer, item.reference].filter(Boolean).join(" · ") || vehicleName(item.vehicle_id)}</p></div>{item.low_stock && <span className="shrink-0 rounded-full bg-amber-100 px-2 py-1 text-[10px] font-bold uppercase text-amber-900 dark:bg-amber-950 dark:text-amber-200">{t("inventory.lowStock")}</span>}</div>
            <p className="mt-4 text-2xl font-bold text-graphite dark:text-cream">{Number(item.quantity).toLocaleString(i18n.language)} <span className="text-sm font-medium text-graphite/50 dark:text-cream/50">{item.unit}</span></p>
            <p className="mt-1 text-xs text-graphite/50 dark:text-cream/50">{vehicleName(item.vehicle_id)}{item.location ? ` · ${item.location}` : ""}</p>
            <button onClick={() => void openMovements(item)} className="mt-4 w-full rounded-lg border border-graphite/15 px-3 py-2 text-sm font-semibold text-graphite dark:border-white/15 dark:text-cream">{t("inventory.movements")}</button>
          </article>
        ))}</div>
      )}
      {selected && <MovementPanel item={selected} movements={movements} canWrite={canWrite} onClose={() => setSelected(null)} onSaved={() => { void openMovements(selected); load(); }} />}
    </div>
  );
}

function ItemForm({ vehicles, onSaved }: { vehicles: Vehicle[]; onSaved: () => void }) {
  const { t } = useTranslation();
  const [name, setName] = useState("");
  const [vehicleId, setVehicleId] = useState("");
  const [quantity, setQuantity] = useState("0");
  const [unit, setUnit] = useState("un");
  const [minimum, setMinimum] = useState("");
  const [reference, setReference] = useState("");
  const [location, setLocation] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  async function submit(event: FormEvent) {
    event.preventDefault(); setSaving(true); setError(null);
    try { await inventory.create({ name, vehicle_id: vehicleId || null, quantity: quantity.replace(",", "."), unit, minimum_quantity: minimum ? minimum.replace(",", ".") : null, reference: reference || null, location: location || null }); onSaved(); }
    catch (cause) { setError(cause instanceof ApiError ? cause.message : t("common.error")); }
    finally { setSaving(false); }
  }
  return <form onSubmit={submit} className="grid min-w-0 gap-3 rounded-xl border border-graphite/10 bg-white p-4 dark:border-white/10 dark:bg-surface-dark-raised sm:grid-cols-2"><label className="text-sm sm:col-span-2">{t("inventory.name")}<input required value={name} onChange={(event) => setName(event.target.value)} className="mt-1 w-full rounded-lg border border-graphite/15 px-3 py-2.5 dark:border-white/15 dark:bg-surface-dark" /></label><label className="text-sm">{t("nav.vehicle")}<select value={vehicleId} onChange={(event) => setVehicleId(event.target.value)} className="mt-1 w-full rounded-lg border border-graphite/15 px-3 py-2.5 dark:border-white/15 dark:bg-surface-dark"><option value="">{t("inventory.shared")}</option>{vehicles.map((vehicle) => <option key={vehicle.id} value={vehicle.id}>{vehicle.name}</option>)}</select></label><label className="text-sm">{t("inventory.reference")}<input value={reference} onChange={(event) => setReference(event.target.value)} className="mt-1 w-full rounded-lg border border-graphite/15 px-3 py-2.5 dark:border-white/15 dark:bg-surface-dark" /></label><label className="text-sm">{t("inventory.quantity")}<input required inputMode="decimal" value={quantity} onChange={(event) => setQuantity(event.target.value)} className="mt-1 w-full rounded-lg border border-graphite/15 px-3 py-2.5 dark:border-white/15 dark:bg-surface-dark" /></label><label className="text-sm">{t("inventory.unit")}<input required value={unit} onChange={(event) => setUnit(event.target.value)} className="mt-1 w-full rounded-lg border border-graphite/15 px-3 py-2.5 dark:border-white/15 dark:bg-surface-dark" /></label><label className="text-sm">{t("inventory.minimum")}<input inputMode="decimal" value={minimum} onChange={(event) => setMinimum(event.target.value)} className="mt-1 w-full rounded-lg border border-graphite/15 px-3 py-2.5 dark:border-white/15 dark:bg-surface-dark" /></label><label className="text-sm">{t("inventory.location")}<input value={location} onChange={(event) => setLocation(event.target.value)} className="mt-1 w-full rounded-lg border border-graphite/15 px-3 py-2.5 dark:border-white/15 dark:bg-surface-dark" /></label>{error && <p role="alert" className="text-sm text-red-700 sm:col-span-2">{error}</p>}<button disabled={saving} className="rounded-lg bg-copper px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-50 sm:col-span-2">{t("garage.save")}</button></form>;
}

function MovementPanel({ item, movements, canWrite, onClose, onSaved }: { item: InventoryItem; movements: StockMovement[] | null; canWrite: boolean; onClose: () => void; onSaved: () => void }) {
  const { t, i18n } = useTranslation();
  const [kind, setKind] = useState<MovementKind>("entry");
  const [quantity, setQuantity] = useState("");
  const [notes, setNotes] = useState("");
  const [error, setError] = useState<string | null>(null);
  async function submit(event: FormEvent) { event.preventDefault(); setError(null); try { await inventory.move(item.id, { kind, quantity: quantity.replace(",", "."), notes: notes || undefined }); setQuantity(""); setNotes(""); onSaved(); } catch (cause) { setError(cause instanceof ApiError ? cause.message : t("common.error")); } }
  return <section className="min-w-0 rounded-xl border border-graphite/10 bg-white p-4 shadow-sm dark:border-white/10 dark:bg-surface-dark-raised"><div className="flex min-w-0 items-center justify-between gap-3"><div className="min-w-0"><h2 className="truncate font-semibold text-graphite dark:text-cream">{item.name}</h2><p className="text-sm text-graphite/50 dark:text-cream/50">{t("inventory.movementHistory")}</p></div><button onClick={onClose} aria-label={t("common.close")} className="grid h-11 w-11 shrink-0 place-items-center rounded-lg border border-graphite/15 dark:border-white/15"><XMarkIcon aria-hidden="true" className="h-5 w-5" /></button></div>{canWrite && <form onSubmit={submit} className="mt-4 grid gap-2 sm:grid-cols-[1fr_1fr_2fr_auto]"><select value={kind} onChange={(event) => setKind(event.target.value as MovementKind)} className="rounded-lg border border-graphite/15 px-3 py-2 dark:border-white/15 dark:bg-surface-dark">{movementKinds.map((value) => <option key={value} value={value}>{t(`inventory.kinds.${value}`)}</option>)}</select><input required inputMode="decimal" placeholder={t("inventory.quantity")} value={quantity} onChange={(event) => setQuantity(event.target.value)} className="rounded-lg border border-graphite/15 px-3 py-2 dark:border-white/15 dark:bg-surface-dark" /><input placeholder={t("inventory.notes")} value={notes} onChange={(event) => setNotes(event.target.value)} className="rounded-lg border border-graphite/15 px-3 py-2 dark:border-white/15 dark:bg-surface-dark" /><button className="rounded-lg bg-copper px-4 py-2 text-sm font-semibold text-white">{t("inventory.register")}</button>{error && <p role="alert" className="text-sm text-red-700 sm:col-span-full">{error}</p>}</form>}<div className="mt-4 divide-y divide-graphite/5 dark:divide-white/5">{movements === null ? <Skeleton lines={3} /> : movements.map((movement) => <div key={movement.id} className="flex flex-wrap items-center justify-between gap-2 py-3 text-sm"><div><p className="font-medium text-graphite dark:text-cream">{t(`inventory.kinds.${movement.kind}`)}</p><p className="text-xs text-graphite/50 dark:text-cream/50">{new Intl.DateTimeFormat(i18n.language).format(new Date(movement.created_at))}{movement.notes ? ` · ${movement.notes}` : ""}</p></div><p className={`font-semibold ${Number(movement.quantity_delta) < 0 ? "text-red-700 dark:text-red-300" : "text-emerald-700 dark:text-emerald-300"}`}>{Number(movement.quantity_delta) > 0 ? "+" : ""}{Number(movement.quantity_delta).toLocaleString(i18n.language)} {item.unit}</p></div>)}</div></section>;
}
