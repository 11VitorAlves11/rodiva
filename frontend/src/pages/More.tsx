import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { ChevronRightIcon } from "@heroicons/react/20/solid";

import { NAV_ICONS } from "../lib/icons";

export function More() {
  const { t } = useTranslation();
  const links = [
    { to: "/import", title: t("import.title"), description: t("import.description"), icon: "reports" as const },
    { to: "/search", title: t("nav.search"), description: t("search.description"), icon: "search" as const },
    { to: "/planner", title: t("nav.planner"), description: t("planner.description"), icon: "planner" as const },
    { to: "/calendar", title: t("nav.calendar"), description: t("calendar.description"), icon: "calendar" as const },
    { to: "/reports", title: t("nav.reports"), description: t("reports.description"), icon: "reports" as const },
    { to: "/inventory", title: t("nav.inventory"), description: t("inventory.description"), icon: "inventory" as const },
    { to: "/equipment", title: t("nav.equipment"), description: t("equipment.description"), icon: "equipment" as const },
    { to: "/inspections", title: t("nav.inspections"), description: t("inspections.description"), icon: "inspections" as const },
    { to: "/activity", title: t("activity.title"), description: t("activity.description"), icon: "activity" as const },
    { to: "/trash", title: t("trash.title"), description: t("trash.description"), icon: "trash" as const },
    { to: "/settings", title: t("nav.settings"), description: t("settings.preferences"), icon: "settings" as const },
  ];

  return (
    <div className="space-y-5">
      <h1 className="text-2xl font-bold text-ink">{t("nav.more")}</h1>
      <div className="grid gap-3">
        {links.map((item) => {
          const ItemIcon = NAV_ICONS[item.icon];
          return (
          <Link key={item.to} to={item.to} className="flex min-h-20 items-center gap-4 rounded-xl border border-line bg-raised p-4 shadow-sm">
            <span className="grid h-11 w-11 shrink-0 place-items-center rounded-lg bg-copper/10 text-brand dark:bg-copper/20">
              <ItemIcon aria-hidden="true" className="h-5 w-5" />
            </span>
            <span className="min-w-0">
              <span className="block font-semibold text-ink">{item.title}</span>
              <span className="block text-sm text-ink-subtle">{item.description}</span>
            </span>
            <ChevronRightIcon aria-hidden="true" className="ml-auto h-5 w-5 shrink-0 text-graphite/30 dark:text-cream/30" />
          </Link>
          );
        })}
      </div>
    </div>
  );
}
