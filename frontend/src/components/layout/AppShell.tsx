import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { NavLink, useLocation } from "react-router-dom";

import { useSession } from "../../lib/session";

const paths = {
  dashboard: "M4 13h6V4H4v9H4Zm0 7h6v-4H4v4Zm10 0h6v-9h-6v9Zm0-16v4h6V4h-6Z",
  garage: "m3 11 2-5h14l2 5v8h-3v-2H6v2H3v-8Zm3.5-3-1.2 3h13.4l-1.2-3h-11ZM7 14a1 1 0 1 0 0 .01V14Zm10 0a1 1 0 1 0 0 .01V14Z",
  history: "M12 4a8 8 0 1 1-7.4 5H2l3.5-4L9 9H6.7A6 6 0 1 0 12 6V4Zm-1 4h2v5H9v-2h2V8Z",
  reminders: "M12 22a2 2 0 0 0 2-2h-4a2 2 0 0 0 2 2Zm7-6v-5a7 7 0 0 0-6-6.9V2h-2v2.1A7 7 0 0 0 5 11v5l-2 2h18l-2-2Z",
  fuel: "M6 3h9v18H6V3Zm2 2v5h5V5H8Zm11 2 2 2v8a2 2 0 0 1-4 0v-4h-2v-2h4V9l-1.5-1.5L19 7Z",
  odometer: "M12 4a8 8 0 1 0 8 8 8 8 0 0 0-8-8Zm0 2a6 6 0 0 1 5.2 9H6.8A6 6 0 0 1 12 6Zm0 2-3 5h6l-3-5Z",
  work: "M14.7 6.3a4 4 0 0 0-5-5L12 3.6 9.6 6 7.3 3.7a4 4 0 0 0 5 5L4 17l3 3 8.3-8.3a4 4 0 0 0-.6-5.4Z",
  expenses: "M3 6h18v13H3V6Zm2 3v7h14V9H5Zm7 1a2.5 2.5 0 1 1 0 5 2.5 2.5 0 0 1 0-5Z",
  notes: "M5 3h14v18H5V3Zm3 4v2h8V7H8Zm0 4v2h8v-2H8Zm0 4v2h5v-2H8Z",
  documents: "M6 2h9l4 4v16H6V2Zm8 2v4h4M9 12h6M9 16h6",
};

function Icon({ name }: { name: keyof typeof paths }) {
  return <svg aria-hidden="true" viewBox="0 0 24 24" className="h-5 w-5 fill-current"><path d={paths[name]} /></svg>;
}

export function AppShell({ children }: { children: ReactNode }) {
  const { t } = useTranslation();
  const { me, signOut } = useSession();
  const location = useLocation();
  const [theme, setTheme] = useState<"light" | "dark">(() => localStorage.getItem("rodiva-theme") === "dark" ? "dark" : "light");
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
  const toggleTheme = () => setTheme((value) => value === "dark" ? "light" : "dark");
  const vehicleId = location.pathname.match(/^\/vehicles\/([^/]+)/)?.[1];
  const vehicleItems = vehicleId ? (["fuel", "odometer", "work", "expenses", "notes", "documents"] as const).map((name) => ({ name, to: `/vehicles/${vehicleId}?section=${name}`, label: t(`${name}.title`) })) : [];
  const linkClass = (active: boolean) => `flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium ${active ? "bg-[#FBE8DF] text-[#9E3E1D]" : "text-slate-600 hover:bg-slate-100"}`;
  const primary = [
    { to: "/", label: t("nav.dashboard"), icon: "dashboard" as const, end: true },
    { to: "/garage", label: t("garage.title"), icon: "garage" as const, end: false },
    { to: "/history", label: t("history.title"), icon: "history" as const, end: false },
    { to: "/reminders", label: t("reminders.title"), icon: "reminders" as const, end: false },
  ];

  return <div className="flex min-h-screen flex-col md:flex-row">
    {!online && <div role="status" className="bg-amber-500 px-4 py-2 text-center text-sm font-medium text-slate-950 md:fixed md:inset-x-64 md:top-0 md:z-40">{t("network.offline")}</div>}
    <header className="flex items-center justify-between border-b border-slate-200 bg-white px-4 py-4 md:hidden"><span className="flex items-center gap-2 text-xl font-bold"><span className="grid h-8 w-8 place-items-center rounded-full border-2 border-current text-[#ef5b2a]">◒</span>Rodiva</span><button aria-label={t("theme.toggle")} onClick={toggleTheme} className="grid h-9 w-9 place-items-center rounded-full border border-slate-300 text-lg">{theme === "dark" ? "☀" : "☾"}</button></header>
    <aside className="hidden w-64 shrink-0 flex-col border-r border-slate-200 bg-white p-4 md:flex"><div className="mb-6 flex items-center gap-3 px-2"><span className="grid h-9 w-9 place-items-center rounded-full bg-[#B94A22] font-bold text-white">R</span><div><p className="font-semibold">Rodiva</p><p className="text-xs text-slate-500">{me?.membership.household_name}</p></div></div><nav className="space-y-1">{primary.map((item) => <NavLink key={item.to} end={item.end} to={item.to} className={({ isActive }) => linkClass(isActive)}><Icon name={item.icon} />{item.label}</NavLink>)}{vehicleItems.length > 0 && <p className="px-3 pb-1 pt-5 text-xs font-semibold uppercase tracking-wide text-slate-400">{t("nav.vehicle")}</p>}{vehicleItems.map((item) => <NavLink key={item.name} to={item.to} className={() => linkClass(location.search === `?section=${item.name}` || (item.name === "fuel" && !location.search))}><Icon name={item.name} />{item.label}</NavLink>)}</nav><div className="mt-auto space-y-1"><button onClick={toggleTheme} className="w-full rounded-lg px-3 py-2 text-left text-sm text-slate-600">{theme === "dark" ? "☀  " + t("theme.light") : "☾  " + t("theme.dark")}</button><button onClick={() => void signOut()} className="w-full px-3 py-2 text-left text-sm text-slate-500">{t("common.signOut")}</button></div></aside>
    <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-6 pb-24 md:pb-6">{!online && <div role="status" className="mb-4 rounded-lg bg-amber-100 px-4 py-3 text-sm font-medium text-amber-900">{t("network.offline")}</div>}{children}</main>
    <nav className="fixed inset-x-0 bottom-0 z-20 grid grid-cols-4 border-t border-slate-200 bg-white/95 p-2 backdrop-blur md:hidden">{primary.map((item) => <NavLink key={item.to} end={item.end} to={item.to} className={({ isActive }) => `flex flex-col items-center gap-1 py-2 text-xs ${isActive ? "text-[#ef5b2a]" : "text-slate-400"}`}><Icon name={item.icon} />{item.label}</NavLink>)}</nav>
  </div>;
}
