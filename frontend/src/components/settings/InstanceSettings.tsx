import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { admin } from "../../lib/api";
import type { InstanceStatus } from "../../lib/api/types";
import { Badge } from "../ui/Badge";

function megabytes(value: number, language: string): string {
  return `${(value / 1024 / 1024).toLocaleString(language, { maximumFractionDigits: 1 })} MB`;
}

/** Instance administration (RF-ADM-009). Owner only; the API enforces that too. */
export function InstanceSettings({ isOwner }: { isOwner: boolean }) {
  const { t, i18n } = useTranslation();
  const [status, setStatus] = useState<InstanceStatus | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    if (!isOwner) return;
    admin
      .status()
      .then(setStatus)
      .catch(() => setFailed(true));
  }, [isOwner]);

  if (!isOwner) return null;

  return (
    <section className="rounded-xl border border-line bg-raised p-5 shadow-sm">
      <h2 className="mb-1 font-semibold text-ink">{t("instance.title")}</h2>
      <p className="mb-4 text-sm text-ink-muted">{t("instance.description")}</p>

      {failed && <p className="text-sm text-danger">{t("common.error")}</p>}
      {!status && !failed && <p className="text-sm text-ink-muted">{t("common.loading")}</p>}

      {status && (
        <dl className="grid gap-x-6 gap-y-3 sm:grid-cols-2">
          <Row label={t("instance.version")}>
            {status.app_name} {status.version} · {status.environment}
          </Row>
          <Row label={t("instance.database")}>
            {status.database_reachable ? (
              <>
                <Badge tone="success">{t("instance.reachable")}</Badge>{" "}
                <span className="text-ink-muted">{status.database_version}</span>
              </>
            ) : (
              <Badge tone="danger">{t("instance.unreachable")}</Badge>
            )}
          </Row>
          <Row label={t("instance.migration")}>
            <code className="text-xs">{status.migration_revision ?? "—"}</code>
          </Row>
          <Row label={t("instance.storage")}>
            {status.storage.exists ? (
              <>
                {megabytes(status.storage.used_bytes, i18n.language)}{" "}
                <span className="text-ink-muted">
                  · {t("instance.free", { value: megabytes(status.storage.free_bytes, i18n.language) })}
                </span>
              </>
            ) : (
              <Badge tone="danger">{t("instance.storageMissing")}</Badge>
            )}
          </Row>
          <Row label={t("instance.tasks")}>
            {status.tasks.notifications_running ? (
              <Badge tone="success">{t("instance.running")}</Badge>
            ) : (
              <Badge tone="warning">{t("instance.stopped")}</Badge>
            )}{" "}
            <span className="text-ink-muted">
              {t("instance.everySeconds", {
                count: status.tasks.notifications_interval_seconds,
              })}
            </span>
          </Row>
          <Row label={t("instance.registration")}>
            {status.public_registration ? t("instance.open") : t("instance.inviteOnly")}
          </Row>

          <div className="sm:col-span-2">
            <dt className="text-sm font-medium text-ink-muted">{t("instance.integrations")}</dt>
            <dd className="mt-1.5 flex flex-wrap gap-1.5">
              {Object.entries(status.integrations).map(([name, on]) => (
                <Badge key={name} tone={on ? "success" : "neutral"}>
                  {t(`instance.integrationNames.${name}`, { defaultValue: name })}
                  {on ? "" : ` · ${t("instance.off")}`}
                </Badge>
              ))}
            </dd>
          </div>

          <div className="sm:col-span-2">
            <dt className="text-sm font-medium text-ink-muted">{t("instance.counts")}</dt>
            <dd className="mt-1.5 flex flex-wrap gap-3 text-sm text-ink">
              {Object.entries(status.counts).map(([name, count]) => (
                <span key={name}>
                  <strong>{count.toLocaleString(i18n.language)}</strong>{" "}
                  {t(`instance.countNames.${name}`, { defaultValue: name })}
                </span>
              ))}
            </dd>
          </div>
        </dl>
      )}
    </section>
  );
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <dt className="text-sm font-medium text-ink-muted">{label}</dt>
      <dd className="mt-0.5 text-sm text-ink">{children}</dd>
    </div>
  );
}
