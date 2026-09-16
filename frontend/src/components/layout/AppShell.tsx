import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { Link, NavLink, useLocation, useNavigate } from "react-router-dom";
import { MoonIcon, SunIcon } from "@heroicons/react/24/outline";

import { NAV_ICONS } from "../../lib/icons";
import { useTheme } from "../../lib/theme";
import { useSession } from "../../lib/session";
import { Logo } from "../ui/Logo";

function Icon({ name, className = "h-5 w-5" }: { name: keyof typeof NAV_ICONS; className?: string }) {
  const Component = NAV_ICONS[name];
  return <Component aria-hidden="true" className={className} />;
}

function initials(name: string | null | undefined, email: string) {
  const source = (name ?? email).trim();
  const parts = source.split(/\s+/).filter(Boolean);
  if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase();
  return source.slice(0, 2).toUpperCase();
}

export function AppShell({ children }: { children: ReactNode }) {
  const { t } = useTranslation();
  const { me, signOut } = useSession();
  const location = useLocation();
  const navigate = useNavigate();
  const [searchTerm, setSearchTerm] = useState("");
  const { resolved: theme, setTheme } = useTheme();
  const [online, setOnline] = useState(navigator.onLine);

  useEffect(() => {
    const update = () => setOnline(navigator.onLine);
    window.addEventListener("online", update);
    window.addEventListener("offline", update);
    return () => {
      window.removeEventListener("online", update);
      window.removeEventListener("offline", update);
    };
  }, []);

  const toggleTheme = () => setTheme(theme === "dark" ? "light" : "dark");
  const vehicleId = location.pathname.match(/^\/vehicles\/([^/]+)/)?.[1];
  const vehicleItems = vehicleId
    ? (["fuel", "charging", "odometer", "work", "expenses", "notes", "documents"] as const).map((name) => ({
        name,
        to: `/vehicles/${vehicleId}?section=${name}`,
        label: t(`${name}.title`),
      }))
    : [];

  const primary = [
    { to: "/", label: t("nav.garage"), icon: "garage" as const, end: true },
    { to: "/history", label: t("nav.history"), icon: "history" as const, end: false },
    { to: "/reminders", label: t("nav.reminders"), icon: "reminders" as const, end: false },
    { to: "/settings", label: t("nav.settings"), icon: "settings" as const, end: false },
  ];
  // Not yet standalone pages — they reuse History's filter until each grows into its own view.
  const secondary = [
    { to: "/history?type=work", label: t("nav.maintenance"), icon: "work" as const, match: "work" },
    { to: "/history?type=expenses", label: t("nav.expenses"), icon: "expenses" as const, match: "expenses" },
  ];
  const mobileTabs = [
    { to: "/", label: t("nav.garage"), icon: "garage" as const, end: true },
    { to: "/history", label: t("nav.history"), icon: "history" as const, end: false },
  ];
  const mobileTabsAfterFab = [
    { to: "/reminders", label: t("nav.reminders"), icon: "reminders" as const, end: false },
    { to: "/more", label: t("nav.more"), icon: "more" as const, end: false },
  ];

  const sidebarLinkClass = (active: boolean) =>
    `flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors ${
      active
        ? "bg-copper/10 text-copper dark:bg-copper/20 dark:text-copper-bright"
        : "text-graphite/70 hover:bg-graphite/5 dark:text-cream/70 dark:hover:bg-white/5"
    }`;
  const mobileTabClass = (active: boolean) =>
    `flex flex-col items-center gap-1 py-2 text-xs ${
      active ? "text-copper dark:text-copper-bright" : "text-graphite/40 dark:text-cream/40"
    }`;

  return (
    <div className="flex min-h-screen min-w-0 flex-col md:flex-row">
      {!online && (
        <div
          role="status"
          className="bg-copper-bright px-4 py-2 text-center text-sm font-medium text-graphite md:fixed md:inset-x-64 md:top-0 md:z-40"
        >
          {t("network.offline")}
        </div>
      )}

      <header className="safe-header flex items-center justify-between border-b border-graphite/10 bg-cream pb-4 dark:border-white/10 dark:bg-surface-dark md:hidden">
        <Link to="/" className="flex items-center gap-2">
          <Logo size={30} />
          <span className="text-lg font-bold text-graphite dark:text-cream">Rodiva</span>
        </Link>
        <button
          aria-label={t("theme.toggle")}
          onClick={toggleTheme}
          className="grid h-9 w-9 place-items-center rounded-full border border-graphite/15 text-graphite dark:border-white/15 dark:text-cream"
        >
          {theme === "dark" ? <SunIcon aria-hidden="true" className="h-5 w-5" /> : <MoonIcon aria-hidden="true" className="h-5 w-5" />}
        </button>
      </header>

      <aside className="hidden w-64 shrink-0 flex-col border-r border-graphite/10 bg-white p-4 dark:border-white/10 dark:bg-surface-dark-raised md:flex">
        <Link to="/" className="mb-6 flex items-center gap-3 px-2">
          <Logo size={34} />
          <div>
            <p className="font-semibold text-graphite dark:text-cream">Rodiva</p>
            <p className="truncate text-xs text-graphite/50 dark:text-cream/50">
              {me?.membership.household_name}
            </p>
          </div>
        </Link>

        <form onSubmit={(event) => { event.preventDefault(); if (searchTerm.trim().length >= 2) navigate(`/search?q=${encodeURIComponent(searchTerm.trim())}`); }} className="mb-4">
          <label className="relative block">
            <span className="sr-only">{t("search.placeholder")}</span>
            <Icon name="search" className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-graphite/40 dark:text-cream/40" />
            <input type="search" value={searchTerm} onChange={(event) => setSearchTerm(event.target.value)} placeholder={t("search.placeholder")} className="w-full rounded-lg border border-graphite/10 bg-graphite/[.03] py-2.5 pl-9 pr-3 text-sm dark:border-white/10 dark:bg-white/[.04]" />
          </label>
        </form>

        <nav className="space-y-1">
          {primary.slice(0, 2).map((item) => (
            <NavLink key={item.to} end={item.end} to={item.to} className={({ isActive }) => sidebarLinkClass(isActive)}>
              <Icon name={item.icon} />
              {item.label}
            </NavLink>
          ))}
          {secondary.map((item) => (
            <Link
              key={item.to}
              to={item.to}
              className={sidebarLinkClass(location.pathname === "/history" && new URLSearchParams(location.search).get("type") === item.match)}
            >
              <Icon name={item.icon} />
              {item.label}
            </Link>
          ))}
          <NavLink to="/planner" className={({ isActive }) => sidebarLinkClass(isActive)}>
            <Icon name="planner" />
            {t("nav.planner")}
          </NavLink>
          <NavLink to="/calendar" className={({ isActive }) => sidebarLinkClass(isActive)}>
            <Icon name="calendar" />
            {t("nav.calendar")}
          </NavLink>
          <NavLink to="/reports" className={({ isActive }) => sidebarLinkClass(isActive)}>
            <Icon name="reports" />
            {t("nav.reports")}
          </NavLink>
          <NavLink to="/inventory" className={({ isActive }) => sidebarLinkClass(isActive)}>
            <Icon name="inventory" />
            {t("nav.inventory")}
          </NavLink>
          <NavLink to="/equipment" className={({ isActive }) => sidebarLinkClass(isActive)}>
            <Icon name="equipment" />
            {t("nav.equipment")}
          </NavLink>
          <NavLink to="/inspections" className={({ isActive }) => sidebarLinkClass(isActive)}>
            <Icon name="inspections" />
            {t("nav.inspections")}
          </NavLink>
          {primary.slice(2).map((item) => (
            <NavLink key={item.to} end={item.end} to={item.to} className={({ isActive }) => sidebarLinkClass(isActive)}>
              <Icon name={item.icon} />
              {item.label}
            </NavLink>
          ))}
          {vehicleItems.length > 0 && (
            <p className="px-3 pb-1 pt-5 text-xs font-semibold uppercase tracking-wide text-graphite/40 dark:text-cream/40">
              {t("nav.vehicle")}
            </p>
          )}
          {vehicleItems.map((item) => (
            <NavLink
              key={item.name}
              to={item.to}
              className={() =>
                sidebarLinkClass(
                  location.search === `?section=${item.name}` || (item.name === "fuel" && !location.search),
                )
              }
            >
              <Icon name={item.name} />
              {item.label}
            </NavLink>
          ))}
        </nav>

        <div className="mt-auto space-y-2 border-t border-graphite/10 pt-3 dark:border-white/10">
          <button
            onClick={() => void signOut()}
            className="flex w-full items-center gap-3 rounded-lg px-2 py-2 text-left"
          >
            <span className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-copper text-sm font-semibold text-white">
              {me ? initials(me.user.name, me.user.email) : ""}
            </span>
            <span className="min-w-0 flex-1">
              <span className="block truncate text-sm font-medium text-graphite dark:text-cream">
                {me?.user.name ?? me?.user.email}
              </span>
              <span className="block text-xs text-graphite/50 dark:text-cream/50">{t("common.signOut")}</span>
            </span>
          </button>
        </div>
      </aside>

      <main className="safe-content mx-auto min-w-0 w-full max-w-6xl flex-1 pt-5 md:py-6">
        {!online && (
          <div role="status" className="mb-4 rounded-lg bg-copper-bright/20 px-4 py-3 text-sm font-medium text-copper-dark dark:text-copper-bright">
            {t("network.offline")}
          </div>
        )}
        {children}
      </main>

      <nav className="safe-bottom fixed inset-x-0 bottom-0 z-20 grid grid-cols-5 items-center border-t border-graphite/10 bg-white/95 backdrop-blur dark:border-white/10 dark:bg-surface-dark/95 md:hidden">
        {mobileTabs.map((item) => (
          <NavLink key={item.to} end={item.end} to={item.to} className={({ isActive }) => mobileTabClass(isActive)}>
            <Icon name={item.icon} />
            {item.label}
          </NavLink>
        ))}
        <Link
          to="/garage?new=1"
          aria-label={t("nav.quickAdd")}
          className="-mt-6 grid h-14 w-14 place-items-center justify-self-center rounded-full bg-copper text-white shadow-lg shadow-copper/40 ring-4 ring-cream dark:ring-surface-dark"
        >
          <Icon name="plus" className="h-6 w-6" />
        </Link>
        {mobileTabsAfterFab.map((item) => (
          <NavLink key={item.to} end={item.end} to={item.to} className={({ isActive }) => mobileTabClass(isActive)}>
            <Icon name={item.icon} />
            {item.label}
          </NavLink>
        ))}
      </nav>
    </div>
  );
}
