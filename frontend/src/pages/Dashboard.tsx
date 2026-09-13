import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { ErrorState } from "../components/ui/ErrorState";
import { Skeleton } from "../components/ui/Skeleton";
import { expenses, fuel, odometer, reminders, vehicles, workRecords } from "../lib/api";
import type { ExpenseRecord, FuelRecord, OdometerReading, Reminder, Vehicle, WorkRecord } from "../lib/api/types";

type VehicleSummary = {
  vehicle: Vehicle;
  readings: OdometerReading[];
  fuel: FuelRecord[];
  work: WorkRecord[];
  expenses: ExpenseRecord[];
  reminders: Reminder[];
};

type Activity = {
  id: string;
  vehicleId: string;
  vehicleName: string;
  date: string;
  title: string;
  detail: string;
};

export function Dashboard() {
  const { t, i18n } = useTranslation();
  const [summaries, setSummaries] = useState<VehicleSummary[] | null>(null);
  const [error, setError] = useState<Error | null>(null);

  const load = () => {
    setError(null);
    vehicles.list().then(async (items) => Promise.all(items.map(async (vehicle) => {
      const [readings, fuelRecords, work, expenseRecords, reminderRecords] = await Promise.all([
        odometer.list(vehicle.id), fuel.list(vehicle.id), workRecords.list(vehicle.id), expenses.list(vehicle.id), reminders.list(vehicle.id),
      ]);
      return { vehicle, readings, fuel: fuelRecords, work, expenses: expenseRecords, reminders: reminderRecords };
    }))).then(setSummaries).catch(setError);
  };

  useEffect(load, []);

  const data = useMemo(() => {
    if (!summaries) return null;
    const costs = summaries.map((summary) => ({
      id: summary.vehicle.id,
      name: summary.vehicle.name,
      value: summary.fuel.reduce((sum, item) => sum + Number(item.total_price), 0)
        + summary.work.reduce((sum, item) => sum + Number(item.total_cost ?? 0), 0)
        + summary.expenses.filter((item) => item.status === "paid").reduce((sum, item) => sum + Number(item.amount), 0),
    }));
    const consumptions = summaries.flatMap((summary) => summary.fuel.map((item) => Number(item.consumption_l_per_100km)).filter(Boolean));
    const activities: Activity[] = summaries.flatMap((summary) => [
      ...summary.fuel.map((item) => ({ id: `fuel-${item.id}`, vehicleId: summary.vehicle.id, vehicleName: summary.vehicle.name, date: item.recorded_on, title: t("dashboard.fuelActivity"), detail: `${Number(item.volume_litres).toLocaleString(i18n.language)} L` })),
      ...summary.work.map((item) => ({ id: `work-${item.id}`, vehicleId: summary.vehicle.id, vehicleName: summary.vehicle.name, date: item.recorded_on, title: item.description, detail: t(`work.${item.kind}`) })),
      ...summary.expenses.map((item) => ({ id: `expense-${item.id}`, vehicleId: summary.vehicle.id, vehicleName: summary.vehicle.name, date: item.issued_on, title: t(`expenses.${item.category}`), detail: Number(item.amount).toLocaleString(i18n.language, { style: "currency", currency: "EUR" }) })),
    ]).sort((a, b) => b.date.localeCompare(a.date)).slice(0, 6);
    return { costs, totalCost: costs.reduce((sum, item) => sum + item.value, 0), averageConsumption: consumptions.length ? consumptions.reduce((sum, value) => sum + value, 0) / consumptions.length : null, activities };
  }, [summaries, i18n.language, t]);

  if (error) return <ErrorState onRetry={load} />;
  if (!summaries || !data) return <Skeleton lines={8} />;
  const currency = (value: number) => value.toLocaleString(i18n.language, { style: "currency", currency: "EUR" });
  const maxCost = Math.max(...data.costs.map((item) => item.value), 1);
  const primary = summaries[0];
  const currentReading = primary?.readings.reduce((highest, item) => Math.max(highest, item.reading), 0) ?? 0;
  const latestConsumption = primary?.fuel.find((item) => item.consumption_l_per_100km)?.consumption_l_per_100km;

  return <div className="rodiva-dashboard space-y-7">
    <div className="flex items-end justify-between gap-4"><div><p className="text-sm font-medium text-[#ef5b2a] md:hidden">{t("dashboard.greeting")}</p><h1 className="text-2xl font-bold text-white md:text-3xl md:text-slate-950">{t("dashboard.title")}</h1><p className="mt-1 hidden text-sm text-slate-500 md:block">{t("dashboard.subtitle")}</p></div><Link to="/garage" className="hidden rounded-lg bg-[#c8471c] px-5 py-3 text-sm font-semibold text-white md:block">＋ {t("dashboard.addRecord")}</Link></div>
    {primary && <Link to={`/vehicles/${primary.vehicle.id}`} className="grid overflow-hidden rounded-xl border border-white/10 bg-[#12181a] shadow-sm md:grid-cols-[300px_1fr] md:border-slate-200 md:bg-white"><div className="grid min-h-44 place-items-center bg-gradient-to-br from-slate-400 via-slate-600 to-slate-900"><svg viewBox="0 0 260 110" className="w-4/5 text-slate-100" aria-hidden="true"><path fill="currentColor" d="M38 70 56 38c5-9 13-14 24-16h87c12 1 21 7 28 17l17 26 22 7c8 3 12 9 12 18v7h-19a24 24 0 0 0-47 0H80a24 24 0 0 0-47 0H14V85c0-8 6-13 24-15Zm33-34L58 65h128l-14-24c-3-4-7-6-13-6H82c-5 0-9 0-11 1Z"/><circle cx="57" cy="96" r="16" fill="#171c20" stroke="currentColor" strokeWidth="5"/><circle cx="203" cy="96" r="16" fill="#171c20" stroke="currentColor" strokeWidth="5"/></svg></div><div className="p-4 md:p-6"><h2 className="text-xl font-bold text-white md:text-2xl md:text-slate-950">{primary.vehicle.name}</h2><p className="text-sm text-slate-400 md:text-slate-500">{[primary.vehicle.make, primary.vehicle.model, primary.vehicle.year].filter(Boolean).join(" · ")}</p><div className="mt-5 grid grid-cols-3 gap-2"><HeroMetric label={t("vehicle.currentOdometer")} value={`${currentReading.toLocaleString(i18n.language)} km`} /><HeroMetric label={t("dashboard.averageConsumption")} value={latestConsumption ? `${Number(latestConsumption).toLocaleString(i18n.language)} L/100 km` : "—"} /><HeroMetric label={t("dashboard.totalCost")} value={currency(data.costs[0]?.value ?? 0)} /></div></div></Link>}
    <div className="grid gap-3 sm:grid-cols-3"><Metric label={t("dashboard.vehicles")} value={String(summaries.length)} /><Metric label={t("dashboard.totalCost")} value={currency(data.totalCost)} /><Metric label={t("dashboard.averageConsumption")} value={data.averageConsumption === null ? "—" : `${data.averageConsumption.toLocaleString(i18n.language, { maximumFractionDigits: 2 })} L/100 km`} /></div>
    {summaries.length === 0 ? <div className="rounded-xl border border-dashed border-slate-300 bg-white p-8 text-center"><p className="font-medium text-slate-900">{t("dashboard.noVehicles")}</p><Link to="/garage" className="mt-3 inline-block text-sm font-medium text-[#9E3E1D]">{t("garage.add")}</Link></div> : <div className="grid gap-5 lg:grid-cols-2"><section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm"><h2 className="font-semibold text-slate-900">{t("dashboard.costByVehicle")}</h2><div className="mt-5 space-y-4">{data.costs.map((item) => <div key={item.id}><div className="mb-1 flex justify-between text-sm"><span>{item.name}</span><span className="font-medium">{currency(item.value)}</span></div><div className="h-2 overflow-hidden rounded-full bg-slate-100"><div className="h-full rounded-full bg-[#B94A22]" style={{ width: `${Math.max(item.value / maxCost * 100, 2)}%` }} /></div></div>)}</div></section><section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm"><h2 className="font-semibold text-slate-900">{t("dashboard.recentActivity")}</h2><ul className="mt-3 divide-y divide-slate-100">{data.activities.map((item) => <li key={item.id}><Link to={`/vehicles/${item.vehicleId}`} className="flex items-center justify-between gap-3 py-3"><div><p className="text-sm font-medium text-slate-900">{item.title}</p><p className="text-xs text-slate-500">{item.vehicleName} · {item.date}</p></div><span className="text-sm text-slate-600">{item.detail}</span></Link></li>)}</ul></section></div>}
  </div>;
}

function Metric({ label, value }: { label: string; value: string }) {
  return <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm"><p className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</p><p className="mt-2 text-2xl font-semibold text-slate-900">{value}</p></div>;
}

function HeroMetric({ label, value }: { label: string; value: string }) {
  return <div className="rounded-lg border border-white/10 bg-white/5 p-3 md:border-slate-200 md:bg-[#fbfaf8]"><p className="truncate text-[10px] font-medium uppercase tracking-wide text-slate-400 md:text-slate-500">{label}</p><p className="mt-2 text-sm font-bold text-white md:text-lg md:text-slate-950">{value}</p></div>;
}
