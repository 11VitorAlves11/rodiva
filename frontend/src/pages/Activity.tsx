import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { EmptyState } from "../components/ui/EmptyState";
import { ErrorState } from "../components/ui/ErrorState";
import { PageHeader } from "../components/ui/PageHeader";
import { Skeleton } from "../components/ui/Skeleton";
import { audit } from "../lib/api";
import type { AuditEvent } from "../lib/api/types";
import type { BadgeTone } from "../components/ui/Badge";

// What each kind of action means, rather than how severe it looks.
const tones: Record<string, BadgeTone> = {
  "record.deleted": "warning",
  "record.purged": "danger",
  "record.restored": "success",
  "vehicle.deleted": "warning",
  "vehicle.restored": "success",
  "member.removed": "danger",
  "member.role_changed": "info",
  "invite.created": "info",
  "invite.revoked": "neutral",
  "api_key.created": "info",
  "api_key.revoked": "neutral",
};

export function Activity() {
  const { t, i18n } = useTranslation();
  const [events, setEvents] = useState<AuditEvent[] | null>(null);
  const [nextBefore, setNextBefore] = useState<string | null>(null);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const load = () => {
    setError(null);
    audit
      .list()
      .then((page) => {
        setEvents(page.items);
        setNextBefore(page.next_before);
      })
      .catch(setError);
  };

  useEffect(load, []);

  const loadMore = async () => {
    if (!nextBefore) return;
    setLoadingMore(true);
    try {
      const page = await audit.list(nextBefore);
      setEvents((current) => [...(current ?? []), ...page.items]);
      setNextBefore(page.next_before);
    } catch (cause) {
      setError(cause instanceof Error ? cause : new Error(t("common.error")));
    } finally {
      setLoadingMore(false);
    }
  };

  if (error) return <ErrorState onRetry={load} />;
  if (!events) return <Skeleton lines={8} />;

  const when = (value: string) =>
    new Intl.DateTimeFormat(i18n.language, { dateStyle: "medium", timeStyle: "short" }).format(
      new Date(value),
    );

  const role = (value: unknown) =>
    typeof value === "string" ? t(`settings.roles.${value}`, { defaultValue: value }) : null;

  // The server stores the data, not the wording, so the detail is phrased here
  // in the reader's own language.
  const detail = (event: AuditEvent) => {
    const context = event.context;
    if (!context) return null;
    if (event.action === "member.role_changed") {
      return `${role(context.from)} → ${role(context.to)}`;
    }
    if (event.action === "member.removed") return role(context.role);
    if (event.action === "invite.created") return role(context.role);
    if (event.action === "api_key.created") {
      return typeof context.scope === "string"
        ? t(`activity.scopes.${context.scope}`, { defaultValue: context.scope })
        : null;
    }
    return null;
  };

  return (
    <div className="space-y-5">
      <PageHeader title={t("activity.title")} description={t("activity.description")} />

      {events.length === 0 ? (
        <EmptyState title={t("activity.empty")} description={t("activity.emptyHint")} />
      ) : (
        <>
          <ul className="divide-y divide-line overflow-hidden rounded-xl border border-line bg-raised">
            {events.map((event) => (
              <li key={event.id} className="flex flex-col gap-1 p-4">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge tone={tones[event.action] ?? "neutral"}>
                    {t(`activity.actions.${event.action}`, { defaultValue: event.action })}
                  </Badge>
                  <p className="min-w-0 truncate font-medium text-ink">{event.summary}</p>
                </div>
                <p className="text-sm text-ink-subtle">
                  {[event.actor_label || t("activity.system"), detail(event), when(event.created_at)]
                    .filter(Boolean)
                    .join(" · ")}
                </p>
              </li>
            ))}
          </ul>
          {nextBefore && (
            <div className="flex justify-center">
              <Button variant="secondary" disabled={loadingMore} onClick={() => void loadMore()}>
                {t("activity.loadMore")}
              </Button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
