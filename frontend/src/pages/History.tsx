import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useSearchParams } from "react-router-dom";
import { ErrorState } from "../components/ui/ErrorState";
import { Skeleton } from "../components/ui/Skeleton";
import { expenses, fuel, odometer, vehicles, workRecords } from "../lib/api";

type Item = { id: string; vehicleId: string; vehicle: string; date: string; type: string; title: string; value: string };
const types = ["fuel", "work", "expenses", "odometer"] as const;

export function History() {
  const { t, i18n } = useTranslation();
  const [items, setItems] = useState<Item[] | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [query, setQuery] = useState("");
  const [searchParams, setSearchParams] = useSearchParams();
  const requestedType = searchParams.get("type");
  const filter = (types as readonly string[]).includes(requestedType ?? "") ? (requestedType as (typeof types)[number]) : "all";
  const load = () => { setError(null); vehicles.list().then(async (list) => Promise.all(list.map(async (vehicle) => {
    const [fuels, work, costs, readings] = await Promise.all([fuel.list(vehicle.id), workRecords.list(vehicle.id), expenses.list(vehicle.id), odometer.list(vehicle.id)]); const base = { vehicleId: vehicle.id, vehicle: vehicle.name };
    return [...fuels.map((item) => ({ ...base, id: item.id, date: item.recorded_on, type: "fuel", title: t("dashboard.fuelActivity"), value: `${item.total_price} €` })), ...work.map((item) => ({ ...base, id: item.id, date: item.recorded_on, type: "work", title: item.description, value: item.total_cost ? `${item.total_cost} €` : "" })), ...costs.map((item) => ({ ...base, id: item.id, date: item.issued_on, type: "expenses", title: t(`expenses.${item.category}`), value: `${item.amount} €` })), ...readings.map((item) => ({ ...base, id: item.id, date: item.recorded_on, type: "odometer", title: t("odometer.title"), value: `${item.reading.toLocaleString(i18n.language)} km` }))];
  }))).then((groups) => setItems(groups.flat().sort((a, b) => b.date.localeCompare(a.date)))).catch(setError); };
  useEffect(load, [i18n.language, t]);
  if (error) return <ErrorState onRetry={load} />;
  if (!items) return <Skeleton lines={8} />;
  const visible = items.filter((item) => (filter === "all" || item.type === filter) && `${item.title} ${item.vehicle}`.toLowerCase().includes(query.toLowerCase()));
  return <div className="space-y-5"><h1 className="text-2xl font-bold text-graphite dark:text-cream">{t("history.title")}</h1><div className="grid gap-3 rounded-xl border border-graphite/10 bg-white p-4 dark:border-white/10 dark:bg-surface-dark-raised sm:grid-cols-[1fr_200px]"><input type="search" placeholder={t("history.search")} value={query} onChange={(event) => setQuery(event.target.value)} className="rounded-lg border border-graphite/15 px-3 py-2.5 dark:border-white/15 dark:bg-surface-dark" /><select value={filter} onChange={(event) => setSearchParams(event.target.value === "all" ? {} : { type: event.target.value })} className="rounded-lg border border-graphite/15 px-3 py-2.5 dark:border-white/15 dark:bg-surface-dark"><option value="all">{t("history.all")}</option><option value="fuel">{t("fuel.title")}</option><option value="work">{t("work.title")}</option><option value="expenses">{t("expenses.title")}</option><option value="odometer">{t("odometer.title")}</option></select></div><section className="overflow-hidden rounded-xl border border-graphite/10 bg-white shadow-sm dark:border-white/10 dark:bg-surface-dark-raised">{visible.length === 0 ? <p className="p-8 text-center text-sm text-graphite/50 dark:text-cream/50">{t("history.empty")}</p> : <ul className="divide-y divide-graphite/5 dark:divide-white/5">{visible.map((item) => <li key={`${item.type}-${item.id}`}><Link to={`/vehicles/${item.vehicleId}?section=${item.type}`} className="flex justify-between gap-4 p-4"><div><p className="font-medium text-graphite dark:text-cream">{item.title}</p><p className="text-sm text-graphite/50 dark:text-cream/50">{item.date} · {item.vehicle}</p></div><span className="text-sm font-medium text-graphite/70 dark:text-cream/70">{item.value}</span></Link></li>)}</ul>}</section></div>;
}
