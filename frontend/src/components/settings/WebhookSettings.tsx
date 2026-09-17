import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { useTranslation } from "react-i18next";

import { Badge } from "../ui/Badge";
import type { BadgeTone } from "../ui/Badge";
import { Button } from "../ui/Button";
import { Field, Input } from "../ui/Field";
import { Skeleton } from "../ui/Skeleton";
import { webhooks } from "../../lib/api";
import { ApiError } from "../../lib/api/client";
import type { Webhook, WebhookDelivery } from "../../lib/api/types";
import { useSession } from "../../lib/session";
import { useConfirm } from "../../components/ui/confirm-context";

const statusTones: Record<string, BadgeTone> = {
  sent: "success",
  pending: "warning",
  failed: "danger",
};

export function WebhookSettings() {
  const { t, i18n } = useTranslation();
  const confirm = useConfirm();
  const { me } = useSession();
  const [items, setItems] = useState<Webhook[] | null>(null);
  const [description, setDescription] = useState("");
  const [url, setUrl] = useState("");
  const [secret, setSecret] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [open, setOpen] = useState<string | null>(null);
  const [deliveries, setDeliveries] = useState<WebhookDelivery[] | null>(null);

  const isOwner = me?.membership.role === "owner";

  const load = () => {
    if (!isOwner) return;
    webhooks
      .list()
      .then(setItems)
      .catch(() => setError(t("common.error")));
  };

  useEffect(load, [isOwner, t]);

  // Only an owner may see or manage endpoints, so the block stays hidden otherwise.
  if (!isOwner) return null;
  if (!items) return <Skeleton lines={4} />;

  const act = async (operation: () => Promise<unknown>) => {
    setBusy(true);
    setError(null);
    try {
      await operation();
      load();
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : t("common.error"));
    } finally {
      setBusy(false);
    }
  };

  async function create(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const created = await webhooks.create({ description, url, events: [] });
      setSecret(created.secret);
      setDescription("");
      setUrl("");
      load();
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : t("common.error"));
    } finally {
      setBusy(false);
    }
  }

  const showDeliveries = async (hook: Webhook) => {
    if (open === hook.id) {
      setOpen(null);
      return;
    }
    setOpen(hook.id);
    setDeliveries(null);
    try {
      setDeliveries(await webhooks.deliveries(hook.id));
    } catch {
      setError(t("common.error"));
    }
  };

  const when = (value: string | null) =>
    value
      ? new Intl.DateTimeFormat(i18n.language, { dateStyle: "short", timeStyle: "short" }).format(
          new Date(value),
        )
      : "—";

  return (
    <section className="space-y-4 rounded-xl border border-line bg-raised p-4 sm:p-6">
      <div>
        <h2 className="text-base font-semibold text-ink">{t("webhooks.title")}</h2>
        <p className="mt-0.5 text-sm text-ink-muted">{t("webhooks.description")}</p>
      </div>

      {items.length > 0 && (
        <ul className="space-y-3">
          {items.map((hook) => (
            <li key={hook.id} className="rounded-lg border border-line p-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="min-w-0">
                  <p className="truncate font-medium text-ink">{hook.description || hook.url}</p>
                  <p className="truncate text-xs text-ink-subtle">{hook.url}</p>
                </div>
                <div className="flex shrink-0 flex-wrap items-center gap-2">
                  <Badge tone={hook.active ? "success" : "neutral"}>
                    {t(hook.active ? "webhooks.active" : "webhooks.paused")}
                  </Badge>
                  <Button size="sm" variant="secondary" disabled={busy} onClick={() => void act(() => webhooks.test(hook.id))}>
                    {t("webhooks.test")}
                  </Button>
                  <Button size="sm" variant="ghost" onClick={() => void showDeliveries(hook)}>
                    {t("webhooks.deliveries")}
                  </Button>
                  <Button
                    size="sm"
                    variant="secondary"
                    disabled={busy}
                    onClick={() => void act(() => webhooks.update(hook.id, { active: !hook.active }))}
                  >
                    {t(hook.active ? "webhooks.pause" : "webhooks.resume")}
                  </Button>
                  <Button
                    size="sm"
                    variant="danger"
                    disabled={busy}
                    onClick={async () => {
                      if (await confirm(t("common.confirmDelete"))) {
                        void act(() => webhooks.remove(hook.id));
                      }
                    }}
                  >
                    {t("common.delete")}
                  </Button>
                </div>
              </div>
              {hook.last_error && <p className="mt-2 text-xs text-danger">{hook.last_error}</p>}

              {open === hook.id &&
                (deliveries === null ? (
                  <Skeleton className="mt-3" lines={3} />
                ) : deliveries.length === 0 ? (
                  <p className="mt-3 text-sm text-ink-subtle">{t("webhooks.noDeliveries")}</p>
                ) : (
                  <ul className="mt-3 divide-y divide-line border-t border-line">
                    {deliveries.map((delivery) => (
                      <li key={delivery.id} className="flex flex-wrap items-center gap-2 py-2 text-sm">
                        <Badge tone={statusTones[delivery.status] ?? "neutral"}>
                          {t(`webhooks.status.${delivery.status}`, { defaultValue: delivery.status })}
                        </Badge>
                        <span className="font-medium text-ink">{delivery.event}</span>
                        <span className="text-ink-subtle">
                          {[
                            when(delivery.created_at),
                            delivery.response_status ? `HTTP ${delivery.response_status}` : null,
                            delivery.attempts > 1
                              ? t("webhooks.attempts", { count: delivery.attempts })
                              : null,
                          ]
                            .filter(Boolean)
                            .join(" · ")}
                        </span>
                        {delivery.status !== "sent" && (
                          <Button
                            size="sm"
                            variant="ghost"
                            className="ml-auto"
                            disabled={busy}
                            onClick={() => void act(() => webhooks.retry(hook.id, delivery.id))}
                          >
                            {t("webhooks.retry")}
                          </Button>
                        )}
                      </li>
                    ))}
                  </ul>
                ))}
            </li>
          ))}
        </ul>
      )}

      {secret && (
        <div className="rounded-lg bg-success-soft p-3 text-sm text-success">
          <p className="font-medium">{t("webhooks.secretOnce")}</p>
          <code className="mt-1 block break-all font-mono text-xs">{secret}</code>
        </div>
      )}

      <form onSubmit={create} className="grid gap-3 sm:grid-cols-2">
        <Field label={t("webhooks.name")}>
          <Input value={description} onChange={(event) => setDescription(event.target.value)} placeholder="n8n" />
        </Field>
        <Field label={t("webhooks.url")} required>
          <Input
            type="url"
            required
            value={url}
            onChange={(event) => setUrl(event.target.value)}
            placeholder="https://"
          />
        </Field>
        {error && <p className="text-sm text-danger sm:col-span-2">{error}</p>}
        <div className="sm:col-span-2">
          <Button type="submit" disabled={busy}>
            {t("webhooks.add")}
          </Button>
        </div>
      </form>
    </section>
  );
}
