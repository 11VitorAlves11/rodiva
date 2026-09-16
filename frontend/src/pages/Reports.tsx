import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";

import { ErrorState } from "../components/ui/ErrorState";
import { Skeleton } from "../components/ui/Skeleton";
import { reports, vehicles } from "../lib/api";
import type { ReportSummary, Vehicle } from "../lib/api/types";

function currency(value: string | number, locale: string, code = "EUR") {
  return new Intl.NumberFormat(locale, {
    style: "currency",
    currency: code,
  }).format(Number(value));
}

function buildQuery(
  selected: string[],
  from: string,
  to: string,
  locale: string,
) {
  const query = new URLSearchParams();
  selected.forEach((id) => query.append("vehicle_id", id));
  if (from) query.set("date_from", from);
  if (to) query.set("date_to", to);
  query.set("locale", locale);
  return `?${query.toString()}`;
}

export function Reports() {
  const { t, i18n } = useTranslation();
  const [vehicleList, setVehicleList] = useState<Vehicle[] | null>(null);
  const [selected, setSelected] = useState<string[]>([]);
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [report, setReport] = useState<ReportSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  function load(ids = selected, dateFrom = from, dateTo = to) {
    setLoading(true);
    setError(null);
    reports
      .summary(buildQuery(ids, dateFrom, dateTo, i18n.language))
      .then(setReport)
      .catch(setError)
      .finally(() => setLoading(false));
  }

  // The initial request deliberately uses the vehicle ids returned by this effect.
  useEffect(() => {
    vehicles
      .list()
      .then((items) => {
        setVehicleList(items);
        const ids = items.map((item) => item.id);
        setSelected(ids);
        load(ids, "", "");
      })
      .catch((cause) => {
        setError(cause);
        setLoading(false);
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const query = buildQuery(selected, from, to, i18n.language);
  if (error) return <ErrorState onRetry={() => load()} />;
  if (!vehicleList || (loading && !report)) return <Skeleton lines={9} />;

  return (
    <div className="min-w-0 space-y-6 print:p-0">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <Link to="/import" className="text-sm font-semibold text-copper">{t("import.title")}</Link>
      <h1 className="text-2xl font-bold text-graphite dark:text-cream">
            {t("reports.title")}
          </h1>
          <p className="mt-1 text-sm text-graphite/50 dark:text-cream/50">
            {t("reports.description")}
          </p>
        </div>
        <div className="flex flex-wrap gap-2 print:hidden">
          <a
            href={reports.csvUrl(query)}
            download
            className="rounded-lg border border-graphite/15 px-3 py-2.5 text-sm font-semibold dark:border-white/15"
          >
            {t("reports.exportCsv")}
          </a>
          <button
            onClick={() => window.print()}
            className="rounded-lg bg-copper px-3 py-2.5 text-sm font-semibold text-white"
          >
            {t("reports.printPdf")}
          </button>
        </div>
      </div>

      <section className="space-y-3 rounded-xl border border-graphite/10 bg-white p-4 dark:border-white/10 dark:bg-surface-dark-raised print:hidden">
        <div className="grid gap-3 sm:grid-cols-2">
          <label className="text-sm">
            {t("reports.from")}
            <input
              type="date"
              value={from}
              onChange={(event) => setFrom(event.target.value)}
              className="mt-1 w-full rounded-lg border px-3 py-2.5 dark:bg-surface-dark"
            />
          </label>
          <label className="text-sm">
            {t("reports.to")}
            <input
              type="date"
              value={to}
              onChange={(event) => setTo(event.target.value)}
              className="mt-1 w-full rounded-lg border px-3 py-2.5 dark:bg-surface-dark"
            />
          </label>
        </div>
        <fieldset>
          <legend className="mb-2 text-sm font-medium">
            {t("reports.vehicles")}
          </legend>
          <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
            {vehicleList.map((vehicle) => (
              <label
                key={vehicle.id}
                className="flex min-h-11 items-center gap-2 rounded-lg border border-graphite/10 px-3 text-sm dark:border-white/10"
              >
                <input
                  type="checkbox"
                  checked={selected.includes(vehicle.id)}
                  onChange={(event) =>
                    setSelected((ids) =>
                      event.target.checked
                        ? [...ids, vehicle.id]
                        : ids.filter((id) => id !== vehicle.id),
                    )
                  }
                />
                {vehicle.name}
              </label>
            ))}
          </div>
        </fieldset>
        <button
          disabled={loading}
          onClick={() => load()}
          className="w-full rounded-lg bg-copper px-4 py-2.5 font-semibold text-white disabled:opacity-50 sm:w-auto"
        >
          {t("reports.apply")}
        </button>
      </section>

      {report && <ReportContent report={report} />}
    </div>
  );
}

function ReportContent({ report }: { report: ReportSummary }) {
  const { t, i18n } = useTranslation();
  const metrics = [
    [
      t("reports.totalCost"),
      currency(report.total_cost, i18n.language, report.currency),
    ],
    [
      t("reports.totalDistance"),
      report.total_distance.toLocaleString(i18n.language),
    ],
    [
      t("reports.inventoryValue"),
      currency(report.inventory_value, i18n.language, report.currency),
    ],
    [
      t("reports.overdue"),
      report.overdue_reminders.toLocaleString(i18n.language),
    ],
  ];
  return (
    <div className="space-y-6">
      <section className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        {metrics.map(([label, value]) => (
          <div
            key={label}
            className="min-w-0 rounded-xl border border-graphite/10 bg-white p-4 dark:border-white/10 dark:bg-surface-dark-raised"
          >
            <p className="break-words text-xs text-graphite/50 dark:text-cream/50">
              {label}
            </p>
            <p className="mt-1 break-words text-xl font-bold text-graphite dark:text-cream">
              {value}
            </p>
          </div>
        ))}
      </section>
      {report.vehicles.length === 0 ? (
        <p className="rounded-xl border border-dashed p-8 text-center text-sm text-graphite/50">
          {t("reports.noData")}
        </p>
      ) : (
        report.vehicles.map((vehicle) => (
          <VehicleReportBlock
            key={vehicle.vehicle_id}
            vehicle={vehicle}
            currencyCode={report.currency}
          />
        ))
      )}
    </div>
  );
}

function VehicleReportBlock({
  vehicle,
  currencyCode,
}: {
  vehicle: ReportSummary["vehicles"][number];
  currencyCode: string;
}) {
  const { t, i18n } = useTranslation();
  const maxCategory = useMemo(
    () => Math.max(...vehicle.categories.map((item) => Number(item.amount)), 1),
    [vehicle.categories],
  );
  return (
    <section className="break-inside-avoid space-y-4 rounded-xl border border-graphite/10 bg-white p-4 dark:border-white/10 dark:bg-surface-dark-raised">
      <div className="flex flex-col gap-1 sm:flex-row sm:items-end sm:justify-between">
        <h2 className="text-lg font-bold">{vehicle.vehicle_name}</h2>
        <p className="text-sm text-graphite/60 dark:text-cream/60">
          {currency(vehicle.total_cost, i18n.language, currencyCode)} ·{" "}
          {vehicle.distance.toLocaleString(i18n.language)}{" "}
          {vehicle.distance_unit}
        </p>
      </div>
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        <Metric
          label={t("reports.costPerDistance", { unit: vehicle.distance_unit })}
          value={
            vehicle.cost_per_distance
              ? currency(vehicle.cost_per_distance, i18n.language, currencyCode)
              : "—"
          }
        />
        <Metric
          label={t("reports.averageConsumption")}
          value={
            vehicle.consumption_average
              ? `${vehicle.consumption_average} ${t("reports.consumptionUnit")}`
              : "—"
          }
        />
        <Metric
          label={t("reports.minimum")}
          value={vehicle.consumption_minimum ?? "—"}
        />
        <Metric
          label={t("reports.maximum")}
          value={vehicle.consumption_maximum ?? "—"}
        />
      </div>
      <div>
        <h3 className="mb-3 font-semibold">{t("reports.categories")}</h3>
        {vehicle.categories.length === 0 ? (
          <p className="text-sm text-graphite/50">{t("reports.noData")}</p>
        ) : (
          <div className="space-y-2">
            {vehicle.categories.map((item) => (
              <div
                key={item.category}
                className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-3"
              >
                <div className="min-w-0">
                  <div className="mb-1 truncate text-xs">{item.category}</div>
                  <div className="h-2 overflow-hidden rounded-full bg-graphite/10 dark:bg-white/10">
                    <div
                      className="h-full rounded-full bg-copper"
                      style={{
                        width: `${Math.max(3, (Number(item.amount) / maxCategory) * 100)}%`,
                      }}
                    />
                  </div>
                </div>
                <span className="text-sm font-semibold">
                  {currency(item.amount, i18n.language, currencyCode)}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
      <div className="overflow-x-auto">
        <h3 className="mb-3 font-semibold">{t("reports.monthly")}</h3>
        <table className="w-full min-w-[560px] text-left text-sm">
          <thead className="text-xs text-graphite/50 dark:text-cream/50">
            <tr>
              <th className="py-2">{t("reports.month")}</th>
              <th>{t("reports.fuel")}</th>
              <th>{t("charging.title")}</th>
              <th>{t("reports.work")}</th>
              <th>{t("reports.expenses")}</th>
              <th>{t("reports.totalCost")}</th>
              <th>{t("reports.totalDistance")}</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-graphite/5 dark:divide-white/5">
            {vehicle.monthly.map((month) => (
              <tr key={month.month}>
                <td className="py-2 font-medium">{month.month}</td>
                <td>{currency(month.fuel, i18n.language, currencyCode)}</td>
                <td>{currency(month.charging, i18n.language, currencyCode)}</td>
                <td>{currency(month.work, i18n.language, currencyCode)}</td>
                <td>{currency(month.expenses, i18n.language, currencyCode)}</td>
                <td className="font-semibold">
                  {currency(month.total, i18n.language, currencyCode)}
                </td>
                <td>
                  {month.distance.toLocaleString(i18n.language)}{" "}
                  {vehicle.distance_unit}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0 rounded-lg bg-graphite/[.03] p-3 dark:bg-white/[.04]">
      <p className="break-words text-[11px] text-graphite/50 dark:text-cream/50">
        {label}
      </p>
      <p className="mt-1 break-words text-sm font-semibold">{value}</p>
    </div>
  );
}
