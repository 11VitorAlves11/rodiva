import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useSearchParams } from "react-router-dom";
import { ErrorState } from "../components/ui/ErrorState";
import { Skeleton } from "../components/ui/Skeleton";
import { charging, expenses, fuel, odometer, vehicles, workRecords } from "../lib/api";
import type { Vehicle } from "../lib/api/types";

type Item = { id: string; vehicleId: string; vehicle: string; date: string; type: string; title: string; value: string };
const types = ["fuel", "charging", "work", "expenses", "odometer"] as const;
const inputClass = "w-full rounded-lg border border-line px-3 py-2.5 bg-raised";

export function History() {
  const { t, i18n } = useTranslation();
  const [items, setItems] = useState<Item[] | null>(null);
  const [vehicleOptions, setVehicleOptions] = useState<Vehicle[]>([]);
  const [error, setError] = useState<Error | null>(null);
  const [attempt, setAttempt] = useState(0);
  const [searchParams, setSearchParams] = useSearchParams();
  const query = searchParams.get("q") ?? "";
  const vehicleId = searchParams.get("vehicle") ?? "";
  const from = searchParams.get("from") ?? "";
  const to = searchParams.get("to") ?? "";
  const sort = searchParams.get("sort") === "asc" ? "asc" : "desc";
  const requestedType = searchParams.get("type");
  const filter = (types as readonly string[]).includes(requestedType ?? "") ? requestedType! : "all";
  const invalidRange = Boolean(from && to && from > to);
  const hasFilters = Boolean(query || vehicleId || from || to || filter !== "all" || sort !== "desc");

  function updateFilter(key: string, value: string) {
    setSearchParams((current) => {
      const next = new URLSearchParams(current);
      if (value) next.set(key, value);
      else next.delete(key);
      return next;
    }, { replace: true });
  }

  useEffect(() => {
    let active = true;
    setError(null);
    setItems(null);
    const money = (value: string) => new Intl.NumberFormat(i18n.language, { style: "currency", currency: "EUR" }).format(Number(value));
    async function load() {
      const list = await vehicles.list();
      const groups = await Promise.all(list.map(async (vehicle) => {
        const [fuels, work, costs, readings, charges] = await Promise.all([
          fuel.list(vehicle.id), workRecords.list(vehicle.id), expenses.list(vehicle.id), odometer.list(vehicle.id), charging.list(vehicle.id),
        ]);
        const base = { vehicleId: vehicle.id, vehicle: vehicle.name };
        return [
          ...charges.map((item) => ({ ...base, id: item.id, date: item.recorded_on, type: "charging", title: t("charging.title"), value: money(item.total_cost) })),
          ...fuels.map((item) => ({ ...base, id: item.id, date: item.recorded_on, type: "fuel", title: t("dashboard.fuelActivity"), value: money(item.total_price) })),
          ...work.map((item) => ({ ...base, id: item.id, date: item.recorded_on, type: "work", title: item.description, value: item.total_cost !== null ? money(item.total_cost) : "" })),
          ...costs.map((item) => ({ ...base, id: item.id, date: item.issued_on, type: "expenses", title: t(`expenses.${item.category}`), value: money(item.amount) })),
          ...readings.map((item) => ({ ...base, id: item.id, date: item.recorded_on, type: "odometer", title: t("odometer.title"), value: `${item.reading.toLocaleString(i18n.language)} ${vehicle.distance_unit}` })),
        ];
      }));
      if (active) {
        setVehicleOptions(list);
        setItems(groups.flat());
      }
    }
    void load().catch((cause: unknown) => { if (active) setError(cause instanceof Error ? cause : new Error(String(cause))); });
    return () => { active = false; };
  }, [i18n.language, t, attempt]);

  if (error) return <ErrorState onRetry={() => setAttempt((value) => value + 1)} />;
  if (!items) return <Skeleton lines={8} />;
  const normalize = (value: string) => value.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLocaleLowerCase(i18n.language);
  const visible = invalidRange ? [] : items.filter((item) =>
    (filter === "all" || item.type === filter) &&
    (!vehicleId || item.vehicleId === vehicleId) &&
    (!from || item.date >= from) && (!to || item.date <= to) &&
    normalize(`${item.title} ${item.vehicle}`).includes(normalize(query.trim())),
  ).sort((a, b) => sort === "asc" ? a.date.localeCompare(b.date) : b.date.localeCompare(a.date));

  return (
    <div className="space-y-5">
      <h1 className="text-2xl font-bold text-ink">{t("history.title")}</h1>
      <div className="grid gap-3 rounded-xl border border-line bg-raised p-4 sm:grid-cols-2 lg:grid-cols-3">
        <label className="text-sm">{t("history.search")}
          <input type="search" value={query} onChange={(event) => updateFilter("q", event.target.value)} className={inputClass} />
        </label>
        <label className="text-sm">{t("search.kindFilter")}
          <select value={filter} onChange={(event) => updateFilter("type", event.target.value === "all" ? "" : event.target.value)} className={inputClass}>
            <option value="all">{t("history.all")}</option>
            {types.map((type) => <option key={type} value={type}>{t(`${type}.title`)}</option>)}
          </select>
        </label>
        <label className="text-sm">{t("search.vehicleFilter")}
          <select value={vehicleId} onChange={(event) => updateFilter("vehicle", event.target.value)} className={inputClass}>
            <option value="">{t("history.allVehicles")}</option>
            {vehicleOptions.map((vehicle) => <option key={vehicle.id} value={vehicle.id}>{vehicle.name}</option>)}
          </select>
        </label>
        <label className="text-sm">{t("history.from")}
          <input type="date" value={from} max={to || undefined} aria-invalid={invalidRange} onChange={(event) => updateFilter("from", event.target.value)} className={inputClass} />
        </label>
        <label className="text-sm">{t("history.to")}
          <input type="date" value={to} min={from || undefined} aria-invalid={invalidRange} onChange={(event) => updateFilter("to", event.target.value)} className={inputClass} />
        </label>
        <label className="text-sm">{t("search.sort")}
          <select value={sort} onChange={(event) => updateFilter("sort", event.target.value === "desc" ? "" : event.target.value)} className={inputClass}>
            <option value="desc">{t("search.sorts.occurred_on_desc")}</option>
            <option value="asc">{t("search.sorts.occurred_on_asc")}</option>
          </select>
        </label>
        {invalidRange && <p role="alert" className="text-sm text-red-700 sm:col-span-2 lg:col-span-3">{t("history.invalidRange")}</p>}
        {hasFilters && <button onClick={() => setSearchParams((current) => {
          const next = new URLSearchParams(current);
          for (const key of ["q", "type", "vehicle", "from", "to", "sort"]) next.delete(key);
          return next;
        }, { replace: true })} className="justify-self-start text-sm font-semibold text-brand">{t("history.clearFilters")}</button>}
      </div>
      <p role="status" className="text-sm text-ink-muted">{t("history.results", { count: visible.length })}</p>
      <section className="overflow-hidden rounded-xl border border-line bg-raised shadow-sm">
        {visible.length === 0 ? <p className="p-8 text-center text-sm text-ink-subtle">{t("history.empty")}</p> : (
          <ul className="divide-y divide-graphite/5 dark:divide-white/5">
            {visible.map((item) => (
              <li key={`${item.type}-${item.id}`}>
                <Link to={`/vehicles/${item.vehicleId}?section=${item.type}`} className="flex min-w-0 flex-col gap-1 p-4 sm:flex-row sm:justify-between sm:gap-4">
                  <div className="min-w-0">
                    <p className="break-words font-medium text-ink">{item.title}</p>
                    <p className="text-sm text-ink-subtle"><time dateTime={item.date}>{new Intl.DateTimeFormat(i18n.language).format(new Date(`${item.date}T12:00:00`))}</time> · {item.vehicle}</p>
                  </div>
                  <span className="shrink-0 text-sm font-medium text-ink-muted">{item.value}</span>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
