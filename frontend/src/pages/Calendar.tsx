import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { ChevronLeftIcon, ChevronRightIcon } from "@heroicons/react/24/outline";

import { ErrorState } from "../components/ui/ErrorState";
import { Skeleton } from "../components/ui/Skeleton";
import { calendarFeed, expenses, plans, reminders, vehicles } from "../lib/api";
import type { CalendarFeedStatus } from "../lib/api/types";

type CalendarEvent = {
  id: string;
  date: string;
  title: string;
  vehicle: string;
  type: "reminder" | "expense" | "plan";
  href: string;
};

const eventStyles: Record<CalendarEvent["type"], string> = {
  reminder: "border-blue-300 bg-blue-50 text-blue-900 dark:border-blue-800 dark:bg-blue-950/50 dark:text-blue-100",
  expense: "border-violet-300 bg-violet-50 text-violet-900 dark:border-violet-800 dark:bg-violet-950/50 dark:text-violet-100",
  plan: "border-amber-300 bg-amber-50 text-amber-900 dark:border-amber-800 dark:bg-amber-950/50 dark:text-amber-100",
};

function isoDate(value: Date) {
  const year = value.getFullYear();
  const month = String(value.getMonth() + 1).padStart(2, "0");
  const day = String(value.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

export function Calendar() {
  const { t, i18n } = useTranslation();
  const [events, setEvents] = useState<CalendarEvent[] | null>(null);
  const [feed, setFeed] = useState<CalendarFeedStatus | null>(null);
  const [feedUrl, setFeedUrl] = useState<string | null>(null);
  const [feedBusy, setFeedBusy] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [month, setMonth] = useState(() => {
    const today = new Date();
    return new Date(today.getFullYear(), today.getMonth(), 1);
  });

  const load = () => {
    setError(null);
    vehicles
      .list()
      .then(async (vehicleList) => {
        const groups = await Promise.all(
          vehicleList.map(async (vehicle) => {
            const [vehicleReminders, vehicleExpenses, vehiclePlans] = await Promise.all([
              reminders.list(vehicle.id),
              expenses.list(vehicle.id),
              plans.list(vehicle.id),
            ]);
            return [
              ...vehicleReminders
                .filter((item) => item.status !== "completed" && item.due_date)
                .map((item) => ({
                  id: `reminder-${item.id}`,
                  date: item.due_date as string,
                  title: item.title,
                  vehicle: vehicle.name,
                  type: "reminder" as const,
                  href: "/reminders",
                })),
              ...vehicleExpenses
                .filter((item) => item.status === "planned" || item.status === "pending")
                .map((item) => ({
                  id: `expense-${item.id}`,
                  date: item.issued_on,
                  title: t(`expenses.${item.category}`),
                  vehicle: vehicle.name,
                  type: "expense" as const,
                  href: `/vehicles/${vehicle.id}?section=expenses`,
                })),
              ...vehiclePlans
                .filter((item) => item.stage !== "completed" && item.due_date)
                .map((item) => ({
                  id: `plan-${item.id}`,
                  date: item.due_date as string,
                  title: item.description,
                  vehicle: vehicle.name,
                  type: "plan" as const,
                  href: "/planner",
                })),
            ];
          }),
        );
        setEvents(groups.flat().sort((a, b) => a.date.localeCompare(b.date)));
      })
      .catch(setError);
  };

  useEffect(load, [t]);

  useEffect(() => {
    calendarFeed.status().then(setFeed).catch(() => setFeed({ active: false, created_at: null }));
  }, []);

  const monthData = useMemo(() => {
    const year = month.getFullYear();
    const monthIndex = month.getMonth();
    const daysInMonth = new Date(year, monthIndex + 1, 0).getDate();
    const mondayOffset = (new Date(year, monthIndex, 1).getDay() + 6) % 7;
    const cells: Array<Date | null> = [
      ...Array.from<null>({ length: mondayOffset }).fill(null),
      ...Array.from({ length: daysInMonth }, (_, index) => new Date(year, monthIndex, index + 1)),
    ];
    while (cells.length % 7) cells.push(null);
    const prefix = `${year}-${String(monthIndex + 1).padStart(2, "0")}`;
    return { cells, events: (events ?? []).filter((item) => item.date.startsWith(prefix)) };
  }, [events, month]);

  if (error) return <ErrorState onRetry={load} />;
  if (!events) return <Skeleton lines={8} />;

  const monthLabel = new Intl.DateTimeFormat(i18n.language, { month: "long", year: "numeric" }).format(month);
  const weekdayLabels = Array.from({ length: 7 }, (_, index) =>
    new Intl.DateTimeFormat(i18n.language, { weekday: "short" }).format(new Date(2024, 0, index + 1)),
  );
  const today = isoDate(new Date());
  const changeMonth = (offset: number) => setMonth((current) => new Date(current.getFullYear(), current.getMonth() + offset, 1));

  const createFeed = async () => {
    setFeedBusy(true);
    try {
      const created = await calendarFeed.create();
      setFeed(created);
      setFeedUrl(`${window.location.origin}${created.feed_path}`);
    } catch (cause) {
      setError(cause instanceof Error ? cause : new Error(t("common.error")));
    } finally {
      setFeedBusy(false);
    }
  };

  const revokeFeed = async () => {
    setFeedBusy(true);
    try {
      await calendarFeed.revoke();
      setFeed({ active: false, created_at: null });
      setFeedUrl(null);
    } catch (cause) {
      setError(cause instanceof Error ? cause : new Error(t("common.error")));
    } finally {
      setFeedBusy(false);
    }
  };

  return (
    <div className="min-w-0 space-y-5">
      <div>
        <h1 className="text-2xl font-bold text-ink">{t("calendar.title")}</h1>
        <p className="mt-1 text-sm text-ink-subtle">{t("calendar.description")}</p>
      </div>
      <div className="flex items-center justify-between gap-2 rounded-xl border border-line bg-raised p-2">
        <button aria-label={t("calendar.previous")} onClick={() => changeMonth(-1)} className="grid h-11 w-11 shrink-0 place-items-center rounded-lg text-ink hover:bg-graphite/5 dark:hover:bg-white/5"><ChevronLeftIcon aria-hidden="true" className="h-5 w-5" /></button>
        <h2 className="min-w-0 text-center font-semibold capitalize text-ink">{monthLabel}</h2>
        <button aria-label={t("calendar.next")} onClick={() => changeMonth(1)} className="grid h-11 w-11 shrink-0 place-items-center rounded-lg text-ink hover:bg-graphite/5 dark:hover:bg-white/5"><ChevronRightIcon aria-hidden="true" className="h-5 w-5" /></button>
      </div>

      <section className="space-y-3 md:hidden">
        {monthData.events.length === 0 ? (
          <p className="rounded-xl border border-dashed border-line-strong bg-raised p-8 text-center text-sm text-ink-subtle">{t("calendar.empty")}</p>
        ) : monthData.events.map((item) => (
          <Link key={item.id} to={item.href} className={`flex min-w-0 items-center gap-3 rounded-xl border-l-4 p-4 ${eventStyles[item.type]}`}>
            <span className="w-12 shrink-0 text-center"><span className="block text-xl font-bold">{Number(item.date.slice(8, 10))}</span><span className="block text-[10px] font-semibold uppercase">{new Intl.DateTimeFormat(i18n.language, { weekday: "short" }).format(new Date(`${item.date}T12:00:00`))}</span></span>
            <span className="min-w-0"><span className="block break-words font-semibold">{item.title}</span><span className="block truncate text-sm opacity-70">{item.vehicle} · {t(`calendar.types.${item.type}`)}</span></span>
          </Link>
        ))}
      </section>

      <section className="hidden overflow-hidden rounded-xl border border-line bg-raised shadow-sm md:block">
        <div className="grid grid-cols-7 border-b border-line">
          {weekdayLabels.map((label) => <div key={label} className="px-2 py-3 text-center text-xs font-semibold uppercase text-graphite/45 dark:text-cream/45">{label}</div>)}
        </div>
        <div className="grid grid-cols-7">
          {monthData.cells.map((day, index) => {
            const key = day ? isoDate(day) : `empty-${index}`;
            const dayEvents = day ? monthData.events.filter((item) => item.date === key) : [];
            return (
              <div key={key} className="min-h-32 min-w-0 border-b border-r border-graphite/5 p-2 dark:border-white/5">
                {day && <span className={`grid h-7 w-7 place-items-center rounded-full text-xs font-medium ${key === today ? "bg-copper text-white" : "text-ink-muted"}`}>{day.getDate()}</span>}
                <div className="mt-1 space-y-1">
                  {dayEvents.map((item) => <Link key={item.id} to={item.href} title={`${item.title} · ${item.vehicle}`} className={`block truncate rounded border px-1.5 py-1 text-[11px] ${eventStyles[item.type]}`}>{item.title}</Link>)}
                </div>
              </div>
            );
          })}
        </div>
      </section>

      <div className="flex flex-wrap gap-3 text-xs text-ink-muted">
        {(["reminder", "expense", "plan"] as const).map((type) => <span key={type} className="flex items-center gap-1.5"><span className={`h-3 w-3 rounded-sm border ${eventStyles[type]}`} />{t(`calendar.types.${type}`)}</span>)}
      </div>

      <section className="min-w-0 rounded-xl border border-line bg-raised p-4 shadow-sm sm:p-5">
        <h2 className="font-semibold text-ink">{t("calendar.feedTitle")}</h2>
        <p className="mt-1 text-sm text-graphite/55 dark:text-cream/55">{t("calendar.feedDescription")}</p>
        {feedUrl && (
          <div className="mt-4 min-w-0 rounded-lg bg-graphite/5 p-3 dark:bg-white/5">
            <p className="text-xs font-semibold text-ink-muted">{t("calendar.feedCopyNow")}</p>
            <code className="mt-2 block overflow-x-auto whitespace-nowrap rounded bg-raised p-2 text-xs text-ink">{feedUrl}</code>
            <button onClick={() => void navigator.clipboard.writeText(feedUrl)} className="mt-2 rounded-md border border-copper/30 px-3 py-2 text-sm font-semibold text-copper">{t("settings.copyLink")}</button>
          </div>
        )}
        <div className="mt-4 flex flex-col gap-2 sm:flex-row">
          <button disabled={feedBusy} onClick={() => void createFeed()} className="rounded-lg bg-copper px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-50">{feed?.active ? t("calendar.feedRenew") : t("calendar.feedCreate")}</button>
          {feed?.active && <button disabled={feedBusy} onClick={() => void revokeFeed()} className="rounded-lg border border-red-300 px-4 py-2.5 text-sm font-semibold text-red-700 disabled:opacity-50 dark:border-red-800 dark:text-red-300">{t("calendar.feedRevoke")}</button>}
        </div>
      </section>
    </div>
  );
}
