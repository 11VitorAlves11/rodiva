import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { Link, NavLink, useLocation, useNavigate } from "react-router-dom";
import { MoonIcon, SunIcon } from "@heroicons/react/24/outline";

import { notifications } from "../../lib/api";
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

  const [unread, setUnread] = useState(0);
  useEffect(() => {
    // The count drives a badge, so a stale one is a cosmetic problem, not a
    // correctness one: poll gently and ignore failures.
    const read = () =>
      notifications
        .list(true)
        .then((page) => setUnread(page.unread))
        .catch(() => {});
    void read();
    const timer = window.setInterval(read, 120_000);
    return () => window.clearInterval(timer);
  }, [location.pathname]);

  const toggleTheme = () => setTheme(theme === "dark" ? "light" : "dark");
  const vehicleId = location.pathname.match(/^\/vehicles\/([^/]+)/)?.[1];
  const vehicleItems = vehicleId
    ? (["fuel", "charging", "odometer", "work", "expenses", "notes", "documents"] as const).map((name) => ({
        name,
        to: `/vehicles/${vehicleId}?section=${name}`,
        label: t(`${name}.title`),
      }))
    : [];

  // Sidebar order, top to bottom. `match` marks the entries that are a filtered
  // History view rather than a page of their own, so they cannot use NavLink:
  // it ignores the query string and would light up all of them at once.
  const sidebarNav = [
    { to: "/", label: t("nav.garage"), icon: "garage" as const, end: true },
    { to: "/history", label: t("nav.history"), icon: "history" as const, end: true },
    { to: "/history?type=work", label: t("nav.maintenance"), icon: "work" as const, match: "work" },
    { to: "/history?type=expenses", label: t("nav.expenses"), icon: "expenses" as const, match: "expenses" },
    { to: "/planner", label: t("nav.planner"), icon: "planner" as const },
    { to: "/calendar", label: t("nav.calendar"), icon: "calendar" as const },
    { to: "/reports", label: t("nav.reports"), icon: "reports" as const },
    { to: "/inventory", label: t("nav.inventory"), icon: "inventory" as const },
    { to: "/equipment", label: t("nav.equipment"), icon: "equipment" as const },
    { to: "/inspections", label: t("nav.inspections"), icon: "inspections" as const },
    { to: "/reminders", label: t("nav.reminders"), icon: "reminders" as const },
    { to: "/notifications", label: t("notifications.title"), icon: "reminders" as const, badge: true },
    { to: "/activity", label: t("activity.title"), icon: "activity" as const },
    { to: "/trash", label: t("trash.title"), icon: "trash" as const },
    { to: "/settings", label: t("nav.settings"), icon: "settings" as const },
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
      active ? "bg-copper/10 text-brand dark:bg-copper/20" : "text-ink-muted hover:bg-sunken"
    }`;
  const mobileTabClass = (active: boolean) =>
    `flex flex-col items-center gap-1 py-2 text-xs ${
      active ? "text-brand" : "text-ink-subtle"
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

      <header className="print-hide safe-header flex items-center justify-between border-b border-line bg-surface pb-4 md:hidden">
        <Link to="/" className="flex items-center gap-2">
          <Logo size={30} />
          <span className="text-lg font-bold text-ink">Rodiva</span>
        </Link>
        <Link
          to="/notifications"
          aria-label={t("notifications.title")}
          className="relative ml-auto mr-2 grid h-9 w-9 place-items-center rounded-full border border-line text-ink"
        >
          <Icon name="reminders" />
          {unread > 0 && (
            <span className="absolute -right-1 -top-1 min-w-5 rounded-full bg-copper px-1 text-center text-[11px] font-semibold text-white">
              {unread > 9 ? "9+" : unread}
            </span>
          )}
        </Link>
        <button
          aria-label={t("theme.toggle")}
          onClick={toggleTheme}
          className="grid h-9 w-9 place-items-center rounded-full border border-line text-ink"
        >
          {theme === "dark" ? <SunIcon aria-hidden="true" className="h-5 w-5" /> : <MoonIcon aria-hidden="true" className="h-5 w-5" />}
        </button>
      </header>

      <aside className="print-hide hidden w-64 shrink-0 flex-col border-r border-line bg-raised p-4 md:flex">
        <Link to="/" className="mb-6 flex items-center gap-3 px-2">
          <Logo size={34} />
          <div>
            <p className="font-semibold text-ink">Rodiva</p>
            <p className="truncate text-xs text-ink-subtle">
              {me?.membership.household_name}
            </p>
          </div>
        </Link>

        <form onSubmit={(event) => { event.preventDefault(); if (searchTerm.trim().length >= 2) navigate(`/search?q=${encodeURIComponent(searchTerm.trim())}`); }} className="mb-4">
          <label className="relative block">
            <span className="sr-only">{t("search.placeholder")}</span>
            <Icon name="search" className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-subtle" />
            <input type="search" value={searchTerm} onChange={(event) => setSearchTerm(event.target.value)} placeholder={t("search.placeholder")} className="w-full rounded-lg border border-line bg-sunken py-2.5 pl-9 pr-3 text-sm" />
          </label>
        </form>

        <nav className="space-y-1">
          {sidebarNav.map((item) =>
            item.match ? (
              <Link
                key={item.to}
                to={item.to}
                className={sidebarLinkClass(
                  location.pathname === "/history" &&
                    new URLSearchParams(location.search).get("type") === item.match,
                )}
              >
                <Icon name={item.icon} />
                {item.label}
              </Link>
            ) : (
              <NavLink
                key={item.to}
                end={item.end}
                to={item.to}
                className={({ isActive }) =>
                  // The plain History entry stays unlit while a filtered one is active.
                  sidebarLinkClass(isActive && !(item.to === "/history" && location.search))
                }
              >
                <Icon name={item.icon} />
                {item.label}
                {item.badge && unread > 0 && (
                  <span className="ml-auto rounded-full bg-copper px-2 py-0.5 text-xs font-semibold text-white">
                    {unread > 99 ? "99+" : unread}
                  </span>
                )}
              </NavLink>
            ),
          )}
          {vehicleItems.length > 0 && (
            <p className="px-3 pb-1 pt-5 text-xs font-semibold uppercase tracking-wide text-ink-subtle">
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

        <div className="mt-auto flex items-center gap-2 border-t border-line pt-3">
          <button
            onClick={() => void signOut()}
            className="flex min-w-0 flex-1 items-center gap-3 rounded-lg px-2 py-2 text-left"
          >
            <span className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-copper text-sm font-semibold text-white">
              {me ? initials(me.user.name, me.user.email) : ""}
            </span>
            <span className="min-w-0 flex-1">
              <span className="block truncate text-sm font-medium text-ink">
                {me?.user.name ?? me?.user.email}
              </span>
              <span className="block text-xs text-ink-subtle">{t("common.signOut")}</span>
            </span>
          </button>
          {/* A sibling of the account button, not nested in it: a button inside
              a button is invalid, and signing out is not what this does. */}
          <button
            aria-label={t("theme.toggle")}
            title={t("theme.toggle")}
            onClick={toggleTheme}
            className="grid h-9 w-9 shrink-0 place-items-center rounded-full border border-line text-ink hover:bg-sunken"
          >
            {theme === "dark" ? (
              <SunIcon aria-hidden="true" className="h-5 w-5" />
            ) : (
              <MoonIcon aria-hidden="true" className="h-5 w-5" />
            )}
          </button>
        </div>
      </aside>

      <main className="safe-content mx-auto min-w-0 w-full max-w-6xl flex-1 pt-5 md:py-6">
        {!online && (
          <div role="status" className="mb-4 rounded-lg bg-copper-bright/20 px-4 py-3 text-sm font-medium text-brand">
            {t("network.offline")}
          </div>
        )}
        {children}
      </main>

      <nav className="print-hide safe-bottom fixed inset-x-0 bottom-0 z-20 grid grid-cols-5 items-center border-t border-line bg-white/95 backdrop-blur dark:bg-surface-dark/95 md:hidden">
        {mobileTabs.map((item) => (
          <NavLink key={item.to} end={item.end} to={item.to} className={({ isActive }) => mobileTabClass(isActive)}>
            <Icon name={item.icon} />
            {item.label}
          </NavLink>
        ))}
        <Link
          to={vehicleId ? `/vehicles/${vehicleId}?section=fuel&new=1` : "/garage?action=fuel"}
          aria-label={t("fuel.add")}
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
