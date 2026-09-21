import { useCallback, useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { ArrowRightIcon, PlusIcon } from "@heroicons/react/20/solid";

import { ErrorState } from "../components/ui/ErrorState";
import { Skeleton } from "../components/ui/Skeleton";
import { charging, expenses, fuel, odometer, reminders, vehicles, workRecords } from "../lib/api";
import { NAV_ICONS } from "../lib/icons";
import { useSession } from "../lib/session";
import type {
  ChargingRecord,
  ExpenseRecord,
  FuelRecord,
  OdometerReading,
  Reminder,
  Vehicle,
  WorkRecord,
} from "../lib/api/types";

type VehicleSummary = {
  vehicle: Vehicle;
  readings: OdometerReading[];
  fuel: FuelRecord[];
  charging: ChargingRecord[];
  work: WorkRecord[];
  expenses: ExpenseRecord[];
  reminders: Reminder[];
};

type Activity = { id: string; kind: "charging" | "fuel" | "work" | "expenses" | "odometer"; date: string; title: string; detail: string; value: string };

const months = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11];

/** Rounds a scale ceiling up to a "nice" step (1/2/5 × a power of ten) so axis
 * labels read like 100/200/300 instead of an arbitrary data maximum. */
function niceScaleMax(value: number): number {
  if (value <= 0) return 100;
  const magnitude = 10 ** Math.floor(Math.log10(value));
  const normalized = value / magnitude;
  const step = normalized <= 1 ? 1 : normalized <= 2 ? 2 : normalized <= 5 ? 5 : 10;
  return step * magnitude;
}

export function Dashboard() {
  const { t, i18n } = useTranslation();
  const { me } = useSession();
  const [summaries, setSummaries] = useState<VehicleSummary[] | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [selected, setSelected] = useState(0);
  const [year, setYear] = useState(new Date().getFullYear());

  const load = () => {
    setError(null);
    vehicles
      .list()
      .then(async (items) =>
        Promise.all(
          items.map(async (vehicle) => {
            const [readings, fuelRecords, work, expenseRecords, reminderRecords, charges] = await Promise.all([
              odometer.list(vehicle.id),
              fuel.list(vehicle.id),
              workRecords.list(vehicle.id),
              expenses.list(vehicle.id),
              reminders.list(vehicle.id),
              charging.list(vehicle.id),
            ]);
            return { vehicle, readings, charging: charges, fuel: fuelRecords, work, expenses: expenseRecords, reminders: reminderRecords };
          }),
        ),
      )
      .then(setSummaries)
      .catch(setError);
  };

  useEffect(load, []);

  const currency = useCallback(
    (value: number) => value.toLocaleString(i18n.language, { style: "currency", currency: "EUR", maximumFractionDigits: 2 }),
    [i18n.language],
  );

  const data = useMemo(() => {
    const primary = summaries?.[selected];
    if (!primary) return null;

    const currentReading = primary.readings.reduce((highest, item) => Math.max(highest, item.reading), 0);
    const consumptions = primary.fuel.map((item) => Number(item.consumption_l_per_100km)).filter(Boolean);
    const averageConsumption = consumptions.length
      ? consumptions.reduce((sum, value) => sum + value, 0) / consumptions.length
      : null;

    const now = new Date();
    const inCurrentMonth = (date: string) => {
      const parsed = new Date(`${date}T12:00:00`);
      return parsed.getFullYear() === now.getFullYear() && parsed.getMonth() === now.getMonth();
    };
    const monthCost =
      primary.charging.filter((item) => inCurrentMonth(item.recorded_on)).reduce((sum, item) => sum + Number(item.total_cost), 0) +
      primary.fuel.filter((item) => inCurrentMonth(item.recorded_on)).reduce((sum, item) => sum + Number(item.total_price), 0) +
      primary.work.filter((item) => inCurrentMonth(item.recorded_on)).reduce((sum, item) => sum + Number(item.total_cost ?? 0), 0) +
      primary.expenses
        .filter((item) => item.status === "paid" && inCurrentMonth(item.issued_on))
        .reduce((sum, item) => sum + Number(item.amount), 0);

    const activities: Activity[] = [
      ...primary.charging.map((item) => ({ id: `charging-${item.id}`, kind: "charging" as const, date: item.recorded_on, title: t("charging.title"), detail: item.location ?? "", value: currency(Number(item.total_cost)) })),
      ...primary.fuel.map((item) => ({
        id: `fuel-${item.id}`,
        kind: "fuel" as const,
        date: item.recorded_on,
        title: t("dashboard.fuelActivity"),
        detail: item.station ?? "",
        value: currency(Number(item.total_price)),
      })),
      ...primary.work.map((item) => ({
        id: `work-${item.id}`,
        kind: "work" as const,
        date: item.recorded_on,
        title: item.description,
        detail: item.supplier ?? t(`work.${item.kind}`),
        value: item.total_cost ? currency(Number(item.total_cost)) : "—",
      })),
      ...primary.expenses.map((item) => ({
        id: `expense-${item.id}`,
        kind: "expenses" as const,
        date: item.issued_on,
        title: t(`expenses.${item.category}`),
        detail: item.supplier ?? "",
        value: currency(Number(item.amount)),
      })),
    ].sort((a, b) => b.date.localeCompare(a.date));

    const monthlyTotals = months.map((month) => {
      const of = (date: string) => {
        const parsed = new Date(`${date}T12:00:00`);
        return parsed.getFullYear() === year && parsed.getMonth() === month;
      };
      return (
        primary.charging.filter((item) => of(item.recorded_on)).reduce((sum, item) => sum + Number(item.total_cost), 0) +
        primary.fuel.filter((item) => of(item.recorded_on)).reduce((sum, item) => sum + Number(item.total_price), 0) +
        primary.work.filter((item) => of(item.recorded_on)).reduce((sum, item) => sum + Number(item.total_cost ?? 0), 0) +
        primary.expenses
          .filter((item) => item.status === "paid" && of(item.issued_on))
          .reduce((sum, item) => sum + Number(item.amount), 0)
      );
    });

    const upcoming = primary.reminders.filter((item) => item.status !== "completed").slice(0, 3);
    const latestFuelType = [...primary.fuel].sort((a, b) => b.recorded_on.localeCompare(a.recorded_on))[0]?.fuel_type;

    return { currentReading, averageConsumption, monthCost, activities, monthlyTotals, upcoming, latestFuelType };
  }, [summaries, selected, year, currency, t]);

  if (error) return <ErrorState onRetry={load} />;
  if (!summaries) return <Skeleton lines={8} />;
  if (!summaries.length) return <div className="space-y-4 rounded-xl border border-dashed border-graphite/20 p-8 text-center"><h1 className="text-xl font-semibold">{t("dashboard.noVehicles")}</h1><Link to="/garage?new=1" className="text-copper">{t("garage.add")}</Link></div>;
  if (!data) return <Skeleton lines={8} />;

  const primary = summaries[selected];
  const scaleMax = niceScaleMax(Math.max(...data.monthlyTotals));
  const axisSteps = [4, 3, 2, 1, 0].map((step) => (scaleMax / 4) * step);
  const compactCurrency = (value: number) => value.toLocaleString(i18n.language, { maximumFractionDigits: 0 }) + " €";
  const yearOptions = [year, year - 1, year - 2];
  const monthLabels = new Intl.DateTimeFormat(i18n.language, { month: "short" });
  const dates = new Intl.DateTimeFormat(i18n.language);

  // A month is read against what this household usually spends, not against a
  // fixed amount: the median of the months that had any spending. The median
  // rather than the mean, so one insurance renewal does not redefine "usual".
  const spent = data.monthlyTotals.filter((value) => value > 0).sort((a, b) => a - b);
  const typical = spent.length
    ? spent.length % 2
      ? spent[(spent.length - 1) / 2]
      : (spent[spent.length / 2 - 1] + spent[spent.length / 2]) / 2
    : 0;
  // Under three months there is no "usual" worth drawing, so the bars stay
  // neutral rather than implying a comparison the data cannot support.
  const hasBaseline = spent.length >= 3;
  const band = (value: number) => {
    if (!hasBaseline || value <= 0) return null;
    const ratio = value / typical;
    if (ratio <= 0.85) return "low" as const;
    if (ratio <= 1.15) return "mid" as const;
    return "high" as const;
  };
  const bandFill = { low: "bg-chart-low", mid: "bg-chart-mid", high: "bg-chart-high" };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-ink">{t("dashboard.title")}</h1>
          <p className="mt-1 hidden text-sm text-ink-subtle md:block">{t("dashboard.subtitle")}</p>
          <p className="text-sm font-medium text-copper md:hidden">
            {t("dashboard.greeting", { name: me?.user.name?.split(" ")[0] ?? me?.user.email })}
          </p>
        </div>
        <Link to="/garage?new=1" className="hidden items-center gap-1.5 rounded-lg bg-copper px-5 py-3 text-sm font-semibold text-white hover:bg-copper-dark md:inline-flex">
          <PlusIcon aria-hidden="true" className="h-4 w-4" />
          {t("dashboard.addRecord")}
        </Link>
      </div>

      {summaries.length === 0 ? (
        <div className="rounded-xl border border-dashed border-line-strong bg-raised p-8 text-center">
          <p className="font-medium text-ink">{t("dashboard.noVehicles")}</p>
          <Link to="/garage?new=1" className="mt-3 inline-block text-sm font-medium text-copper">
            {t("garage.add")}
          </Link>
        </div>
      ) : (
        <>
          {summaries.length > 1 && (
            <div className="flex gap-2 overflow-x-auto pb-1">
              {summaries.map((summary, index) => (
                <button
                  key={summary.vehicle.id}
                  onClick={() => setSelected(index)}
                  className={`shrink-0 rounded-full px-4 py-2 text-sm font-medium ${
                    index === selected
                      ? "bg-copper text-white"
                      : "bg-raised text-graphite/60 dark:bg-surface-dark-raised dark:text-cream/60"
                  }`}
                >
                  {summary.vehicle.name}
                </button>
              ))}
            </div>
          )}

          <section className="grid overflow-hidden rounded-xl border border-line bg-raised shadow-sm md:grid-cols-[300px_1fr]">
            <div className="grid min-h-44 place-items-center bg-gradient-to-br from-slate-400 via-slate-600 to-slate-900">
              {primary.vehicle.photo_url ? (
                <img src={primary.vehicle.photo_url} alt="" className="h-full w-full object-cover" />
              ) : (
                <svg viewBox="0 0 260 110" className="w-4/5 text-slate-100" aria-hidden="true">
                  <path
                    fill="currentColor"
                    d="M38 70 56 38c5-9 13-14 24-16h87c12 1 21 7 28 17l17 26 22 7c8 3 12 9 12 18v7h-19a24 24 0 0 0-47 0H80a24 24 0 0 0-47 0H14V85c0-8 6-13 24-15Zm33-34L58 65h128l-14-24c-3-4-7-6-13-6H82c-5 0-9 0-11 1Z"
                  />
                  <circle cx={57} cy={96} r={16} fill="#171c20" stroke="currentColor" strokeWidth={5} />
                  <circle cx={203} cy={96} r={16} fill="#171c20" stroke="currentColor" strokeWidth={5} />
                </svg>
              )}
            </div>
            <div className="p-4 md:p-6">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <h2 className="text-xl font-bold text-ink md:text-2xl">{primary.vehicle.name}</h2>
                  <p className="text-sm text-ink-subtle">
                    {[primary.vehicle.make, primary.vehicle.model, primary.vehicle.year, data.latestFuelType].filter(Boolean).join(" · ")}
                  </p>
                </div>
                <Link to={`/vehicles/${primary.vehicle.id}`} className="rounded-md border border-line px-3 py-1.5 text-sm font-medium text-ink">
                  {t("dashboard.edit")}
                </Link>
              </div>
              <div className="mt-5 grid grid-cols-1 gap-2 sm:grid-cols-3">
                <StatTile label={t("vehicle.currentOdometer")} value={`${data.currentReading.toLocaleString(i18n.language)} ${primary.vehicle.distance_unit}`} />
                <StatTile label={t("dashboard.averageConsumption")} value={data.averageConsumption === null ? "—" : `${data.averageConsumption.toLocaleString(i18n.language, { maximumFractionDigits: 1 })} L/100 km`} />
                <StatTile label={t("dashboard.monthCost")} value={currency(data.monthCost)} />
              </div>
            </div>
          </section>

          <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
            <section className="rounded-xl border border-line bg-raised p-5 shadow-sm">
              <div className="mb-3 flex items-center justify-between">
                <h2 className="font-semibold text-ink">{t("dashboard.recentHistory")}</h2>
                <Link to="/history" className="inline-flex items-center gap-1 text-sm font-medium text-copper">
                  {t("dashboard.viewAll")}
                  <ArrowRightIcon aria-hidden="true" className="h-3.5 w-3.5" />
                </Link>
              </div>
              {data.activities.length === 0 ? (
                <p className="py-4 text-sm text-ink-subtle">{t("history.empty")}</p>
              ) : (
                <ul className="divide-y divide-graphite/5 dark:divide-white/5">
                  {data.activities.slice(0, 5).map((item) => {
                    const ActivityIcon = NAV_ICONS[item.kind];
                    return (
                    <li key={item.id} className="flex items-center gap-3 py-3">
                      <span className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-copper/10 text-brand dark:bg-copper/20">
                        <ActivityIcon aria-hidden="true" className="h-4 w-4" />
                      </span>
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-sm font-medium text-ink">{item.title}</p>
                        <p className="truncate text-xs text-ink-subtle">
                          {new Intl.DateTimeFormat(i18n.language).format(new Date(`${item.date}T12:00:00`))}
                          {item.detail ? ` · ${item.detail}` : ""}
                        </p>
                      </div>
                      <span className="shrink-0 text-sm font-medium text-ink-muted">{item.value}</span>
                    </li>
                    );
                  })}
                </ul>
              )}
            </section>

            <section className="rounded-xl border border-line bg-raised p-5 shadow-sm">
              <div className="mb-3 flex items-center justify-between">
                <h2 className="font-semibold text-ink">{t("dashboard.monthlyExpenses")}</h2>
                <select
                  value={year}
                  onChange={(event) => setYear(Number(event.target.value))}
                  className="rounded-md border border-line bg-raised px-2 py-1 text-sm"
                >
                  {yearOptions.map((option) => (
                    <option key={option} value={option}>{option}</option>
                  ))}
                </select>
              </div>
              <div className="flex gap-2">
                <div className="flex h-36 flex-col justify-between text-right text-[10px] text-ink-subtle">
                  {axisSteps.map((step) => (
                    <span key={step}>{compactCurrency(step)}</span>
                  ))}
                </div>
                <div className="relative min-w-0 flex-1">
                  <div className="pointer-events-none absolute inset-0 flex h-36 flex-col justify-between">
                    {axisSteps.map((step) => (
                      <div key={step} className="border-t border-line" />
                    ))}
                  </div>
                  <div className="relative flex h-36 items-end gap-1.5">
                    {/* The typical month, drawn: above or below it is readable
                        from the geometry, so the banding is never colour alone. */}
                    {hasBaseline && (
                      <div
                        aria-hidden="true"
                        className="pointer-events-none absolute inset-x-0 border-t border-dashed border-ink-subtle"
                        style={{ bottom: `${(typical / scaleMax) * 100}%` }}
                      />
                    )}
                    {data.monthlyTotals.map((value, month) => {
                      const tone = band(value);
                      return (
                        <div key={month} className="group relative flex h-full flex-1 items-end justify-center">
                          <div
                            className={`w-full max-w-6 rounded-t ${tone ? bandFill[tone] : "bg-ink-subtle"}`}
                            style={{ height: `${Math.max((value / scaleMax) * 100, value > 0 ? 2 : 0)}%` }}
                          />
                          {value > 0 && (
                            <span className="pointer-events-none absolute bottom-full mb-1 hidden whitespace-nowrap rounded bg-graphite px-1.5 py-0.5 text-[10px] font-medium text-cream group-hover:block dark:bg-cream dark:text-graphite">
                              {currency(value)}
                              {tone && ` · ${t(`dashboard.spending.${tone}`)}`}
                            </span>
                          )}
                        </div>
                      );
                    })}
                  </div>
                  <div className="mt-1 grid grid-cols-12 gap-1.5">
                    {months.map((month) => (
                      <span key={month} className="min-w-0 text-center text-[8px] uppercase text-ink-subtle sm:text-[10px]">
                        {monthLabels.format(new Date(year, month, 1))}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
              {hasBaseline && (
                <ul className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1 text-[11px] text-ink-muted">
                  {(["low", "mid", "high"] as const).map((tone) => (
                    <li key={tone} className="flex items-center gap-1.5">
                      <span aria-hidden="true" className={`h-2.5 w-2.5 rounded-sm ${bandFill[tone]}`} />
                      {t(`dashboard.spending.${tone}`)}
                    </li>
                  ))}
                  <li className="flex items-center gap-1.5">
                    <span aria-hidden="true" className="h-0 w-4 border-t border-dashed border-ink-subtle" />
                    {t("dashboard.spending.typical", { amount: compactCurrency(typical) })}
                  </li>
                </ul>
              )}
            </section>
          </div>

          <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
            <section className="rounded-xl border border-line bg-raised p-5 shadow-sm">
              <div className="mb-3 flex items-center justify-between">
                <h2 className="font-semibold text-ink">{t("dashboard.upcomingMaintenance")}</h2>
                <Link to="/reminders" className="inline-flex items-center gap-1 text-sm font-medium text-copper">
                  {t("dashboard.viewAll")}
                  <ArrowRightIcon aria-hidden="true" className="h-3.5 w-3.5" />
                </Link>
              </div>
              {data.upcoming.length === 0 ? (
                <p className="py-4 text-sm text-ink-subtle">{t("reminders.empty")}</p>
              ) : (
                <ul className="divide-y divide-graphite/5 dark:divide-white/5">
                  {data.upcoming.map((item) => (
                    <li key={item.id} className="flex items-center justify-between gap-3 py-3">
                      <span className="text-sm font-medium text-ink">{item.title}</span>
                      <span className="text-sm text-ink-subtle">
                        {[item.due_date ? dates.format(new Date(`${item.due_date}T12:00:00`)) : null, item.due_odometer ? `${item.due_odometer.toLocaleString(i18n.language)} km` : null].filter(Boolean).join(" · ")}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </section>

            <section className="rounded-xl border border-line bg-raised p-5 shadow-sm">
              <div className="mb-3 flex items-center justify-between">
                <h2 className="font-semibold text-ink">{t("dashboard.vehicleInfo")}</h2>
                <Link to={`/vehicles/${primary.vehicle.id}`} className="text-sm font-medium text-copper">
                  {t("dashboard.edit")}
                </Link>
              </div>
              <dl className="space-y-2 text-sm">
                <InfoRow label={t("dashboard.licensePlate")} value={primary.vehicle.license_plate ?? "—"} />
                <InfoRow label={t("dashboard.brandModel")} value={[primary.vehicle.make, primary.vehicle.model].filter(Boolean).join(" ") || "—"} />
                <InfoRow label={t("garage.year")} value={primary.vehicle.year?.toString() ?? "—"} />
                <InfoRow label={t("dashboard.fuelType")} value={data.latestFuelType ?? "—"} />
                <InfoRow label={t("dashboard.averageConsumption")} value={data.averageConsumption === null ? "—" : `${data.averageConsumption.toLocaleString(i18n.language, { maximumFractionDigits: 1 })} L/100 km`} />
                <InfoRow label="VIN" value={primary.vehicle.vin ?? "—"} />
              </dl>
            </section>
          </div>
        </>
      )}
    </div>
  );
}

function StatTile({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg bg-graphite/5 p-3 dark:bg-white/5">
      <p className="truncate text-[10px] font-medium uppercase tracking-wide text-ink-subtle">{label}</p>
      <p className="mt-1 text-sm font-bold text-ink md:text-base">{value}</p>
    </div>
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-4 border-b border-graphite/5 py-2 last:border-0 dark:border-white/5">
      <dt className="text-ink-subtle">{label}</dt>
      <dd className="font-medium text-ink">{value}</dd>
    </div>
  );
}
