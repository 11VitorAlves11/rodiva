import { useTranslation } from "react-i18next";

import { useSession } from "../lib/session";

function initials(name: string | null | undefined, email: string) {
  const source = (name ?? email).trim();
  const parts = source.split(/\s+/).filter(Boolean);
  if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase();
  return source.slice(0, 2).toUpperCase();
}

export function Settings() {
  const { t, i18n } = useTranslation();
  const { me, signOut } = useSession();

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-graphite dark:text-cream">{t("settings.title")}</h1>

      <section className="flex items-center gap-4 rounded-xl border border-graphite/10 bg-white p-5 shadow-sm dark:border-white/10 dark:bg-surface-dark-raised">
        <span className="grid h-14 w-14 shrink-0 place-items-center rounded-full bg-copper text-lg font-semibold text-white">
          {me ? initials(me.user.name, me.user.email) : ""}
        </span>
        <div className="min-w-0">
          <p className="truncate font-semibold text-graphite dark:text-cream">{me?.user.name ?? me?.user.email}</p>
          <p className="truncate text-sm text-graphite/50 dark:text-cream/50">{me?.user.email}</p>
          <p className="mt-1 text-sm text-graphite/50 dark:text-cream/50">{me?.membership.household_name}</p>
        </div>
      </section>

      <section className="rounded-xl border border-graphite/10 bg-white p-5 shadow-sm dark:border-white/10 dark:bg-surface-dark-raised">
        <h2 className="mb-4 font-semibold text-graphite dark:text-cream">{t("settings.preferences")}</h2>
        <div className="flex items-center justify-between gap-4 py-2">
          <span className="text-sm text-graphite/70 dark:text-cream/70">{t("settings.language")}</span>
          <select
            value={i18n.language}
            onChange={(event) => void i18n.changeLanguage(event.target.value)}
            className="rounded-md border border-graphite/15 bg-white px-3 py-2 text-sm dark:border-white/15 dark:bg-surface-dark"
          >
            <option value="pt-PT">Português</option>
            <option value="en">English</option>
          </select>
        </div>
      </section>

      <button
        onClick={() => void signOut()}
        className="w-full rounded-lg border border-copper/30 px-4 py-3 text-sm font-semibold text-copper hover:bg-copper/5 dark:text-copper-bright"
      >
        {t("common.signOut")}
      </button>
    </div>
  );
}
