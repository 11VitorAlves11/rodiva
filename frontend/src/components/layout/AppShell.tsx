import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { Link, NavLink, useLocation } from "react-router-dom";

import { useSession } from "../../lib/session";
import { Logo } from "../ui/Logo";

const paths = {
  garage: "m3 11 2-5h14l2 5v8h-3v-2H6v2H3v-8Zm3.5-3-1.2 3h13.4l-1.2-3h-11ZM7 14a1 1 0 1 0 0 .01V14Zm10 0a1 1 0 1 0 0 .01V14Z",
  history: "M12 4a8 8 0 1 1-7.4 5H2l3.5-4L9 9H6.7A6 6 0 1 0 12 6V4Zm-1 4h2v5H9v-2h2V8Z",
  reminders: "M12 22a2 2 0 0 0 2-2h-4a2 2 0 0 0 2 2Zm7-6v-5a7 7 0 0 0-6-6.9V2h-2v2.1A7 7 0 0 0 5 11v5l-2 2h18l-2-2Z",
  settings: "M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8Zm8.4 4a7.9 7.9 0 0 0-.15-1.5l2.1-1.6-2-3.5-2.5 1a8 8 0 0 0-2.6-1.5L14.8 2H9.2l-.45 2.9a8 8 0 0 0-2.6 1.5l-2.5-1-2 3.5 2.1 1.6a7.9 7.9 0 0 0 0 3l-2.1 1.6 2 3.5 2.5-1a8 8 0 0 0 2.6 1.5l.45 2.9h5.6l.45-2.9a8 8 0 0 0 2.6-1.5l2.5 1 2-3.5-2.1-1.6c.1-.5.15-1 .15-1.5Z",
  more: "M12 6.5a2 2 0 1 0 0-4 2 2 0 0 0 0 4Zm0 7.5a2 2 0 1 0 0-4 2 2 0 0 0 0 4Zm0 7.5a2 2 0 1 0 0-4 2 2 0 0 0 0 4Z",
  plus: "M11 5h2v6h6v2h-6v6h-2v-6H5v-2h6V5Z",
  fuel: "M6 3h9v18H6V3Zm2 2v5h5V5H8Zm11 2 2 2v8a2 2 0 0 1-4 0v-4h-2v-2h4V9l-1.5-1.5L19 7Z",
  odometer: "M12 4a8 8 0 1 0 8 8 8 8 0 0 0-8-8Zm0 2a6 6 0 0 1 5.2 9H6.8A6 6 0 0 1 12 6Zm0 2-3 5h6l-3-5Z",
  work: "M14.7 6.3a4 4 0 0 0-5-5L12 3.6 9.6 6 7.3 3.7a4 4 0 0 0 5 5L4 17l3 3 8.3-8.3a4 4 0 0 0-.6-5.4Z",
  expenses: "M3 6h18v13H3V6Zm2 3v7h14V9H5Zm7 1a2.5 2.5 0 1 1 0 5 2.5 2.5 0 0 1 0-5Z",
  notes: "M5 3h14v18H5V3Zm3 4v2h8V7H8Zm0 4v2h8v-2H8Zm0 4v2h5v-2H8Z",
  documents: "M6 2h9l4 4v16H6V2Zm8 2v4h4M9 12h6M9 16h6",
};

function Icon({ name, className = "h-5 w-5" }: { name: keyof typeof paths; className?: string }) {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24" className={`${className} fill-current`}>
      <path d={paths[name]} />
    </svg>
  );
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
  const [theme, setTheme] = useState<"light" | "dark">(
    () => (localStorage.getItem("rodiva-theme") === "dark" ? "dark" : "light"),
  );
  const [online, setOnline] = useState(navigator.onLine);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    document.documentElement.style.colorScheme = theme;
    localStorage.setItem("rodiva-theme", theme);
  }, [theme]);

  useEffect(() => {
    const update = () => setOnline(navigator.onLine);
    window.addEventListener("online", update);
    window.addEventListener("offline", update);
    return () => {
      window.removeEventListener("online", update);
      window.removeEventListener("offline", update);
    };
  }, []);

  const toggleTheme = () => setTheme((value) => (value === "dark" ? "light" : "dark"));
  const vehicleId = location.pathname.match(/^\/vehicles\/([^/]+)/)?.[1];
  const vehicleItems = vehicleId
    ? (["fuel", "odometer", "work", "expenses", "notes", "documents"] as const).map((name) => ({
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
    { to: "/settings", label: t("nav.more"), icon: "more" as const, end: false },
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
    <div className="flex min-h-screen flex-col md:flex-row">
      {!online && (
        <div
          role="status"
          className="bg-copper-bright px-4 py-2 text-center text-sm font-medium text-graphite md:fixed md:inset-x-64 md:top-0 md:z-40"
        >
          {t("network.offline")}
        </div>
      )}

      <header className="flex items-center justify-between border-b border-graphite/10 bg-cream px-4 py-4 dark:border-white/10 dark:bg-surface-dark md:hidden">
        <Link to="/" className="flex items-center gap-2">
          <Logo size={30} />
          <span className="text-lg font-bold text-graphite dark:text-cream">Rodiva</span>
        </Link>
        <button
          aria-label={t("theme.toggle")}
          onClick={toggleTheme}
          className="grid h-9 w-9 place-items-center rounded-full border border-graphite/15 text-lg text-graphite dark:border-white/15 dark:text-cream"
        >
          {theme === "dark" ? "☀" : "☾"}
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

      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-6 pb-24 md:pb-6">
        {!online && (
          <div role="status" className="mb-4 rounded-lg bg-copper-bright/20 px-4 py-3 text-sm font-medium text-copper-dark dark:text-copper-bright">
            {t("network.offline")}
          </div>
        )}
        {children}
      </main>

      <nav className="fixed inset-x-0 bottom-0 z-20 grid grid-cols-5 items-center border-t border-graphite/10 bg-white/95 px-2 pb-[env(safe-area-inset-bottom)] backdrop-blur dark:border-white/10 dark:bg-surface-dark/95 md:hidden">
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
