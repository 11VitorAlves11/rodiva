import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { Badge } from "../components/ui/Badge";
import type { BadgeTone } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { EmptyState } from "../components/ui/EmptyState";
import { ErrorState } from "../components/ui/ErrorState";
import { PageHeader } from "../components/ui/PageHeader";
import { Skeleton } from "../components/ui/Skeleton";
import { notifications } from "../lib/api";
import type { NotificationItem } from "../lib/api/types";

const urgencyTones: Record<string, BadgeTone> = {
  overdue: "danger",
  very_urgent: "danger",
  urgent: "warning",
  upcoming: "info",
  future: "neutral",
};

export function Notifications() {
  const { t, i18n } = useTranslation();
  const [items, setItems] = useState<NotificationItem[] | null>(null);
  const [unread, setUnread] = useState(0);
  const [error, setError] = useState<Error | null>(null);
  const [busy, setBusy] = useState(false);

  const load = () => {
    setError(null);
    notifications
      .list()
      .then((page) => {
        setItems(page.items);
        setUnread(page.unread);
      })
      .catch(setError);
  };

  useEffect(load, []);

  const markAll = async () => {
    setBusy(true);
    try {
      await notifications.markAllRead();
      load();
    } catch (cause) {
      setError(cause instanceof Error ? cause : new Error(t("common.error")));
    } finally {
      setBusy(false);
    }
  };

  const open = async (item: NotificationItem) => {
    if (item.read_at) return;
    try {
      await notifications.markRead(item.id);
      load();
    } catch {
      // Reading is a convenience; a failure here should not block navigation.
    }
  };

  if (error) return <ErrorState onRetry={load} />;
  if (!items) return <Skeleton lines={7} />;

  const when = (value: string) =>
    new Intl.DateTimeFormat(i18n.language, { dateStyle: "medium", timeStyle: "short" }).format(
      new Date(value),
    );

  return (
    <div className="space-y-5">
      <PageHeader
        title={t("notifications.title")}
        description={t("notifications.description")}
        actions={
          unread > 0 && (
            <Button variant="secondary" size="sm" disabled={busy} onClick={() => void markAll()}>
              {t("notifications.markAllRead")}
            </Button>
          )
        }
      />

      {items.length === 0 ? (
        <EmptyState title={t("notifications.empty")} description={t("notifications.emptyHint")} />
      ) : (
        <ul className="divide-y divide-line overflow-hidden rounded-xl border border-line bg-raised">
          {items.map((item) => {
            const urgency = item.context?.urgency;
            return (
              <li key={item.id} className={item.read_at ? "" : "bg-copper/[.04]"}>
                <Link
                  to={item.vehicle_id ? `/vehicles/${item.vehicle_id}` : "/reminders"}
                  onClick={() => void open(item)}
                  className="flex flex-col gap-1 p-4"
                >
                  <div className="flex flex-wrap items-center gap-2">
                    {!item.read_at && (
                      <span aria-label={t("notifications.unread")} className="h-2 w-2 rounded-full bg-copper" />
                    )}
                    {urgency && (
                      <Badge tone={urgencyTones[urgency] ?? "neutral"}>
                        {t(`reminders.${urgency}`, { defaultValue: urgency })}
                      </Badge>
                    )}
                    <p className="min-w-0 truncate font-semibold text-ink">{item.title}</p>
                  </div>
                  {item.body && <p className="text-sm text-ink-muted">{item.body}</p>}
                  <p className="text-sm text-ink-subtle">
                    {[item.context?.vehicle_name, when(item.created_at)].filter(Boolean).join(" · ")}
                  </p>
                </Link>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
