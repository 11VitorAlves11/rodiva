import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { EmptyState } from "../components/ui/EmptyState";
import { ErrorState } from "../components/ui/ErrorState";
import { PageHeader } from "../components/ui/PageHeader";
import { Skeleton } from "../components/ui/Skeleton";
import { trash, vehicles } from "../lib/api";
import { ApiError } from "../lib/api/client";
import type { TrashItem, Vehicle } from "../lib/api/types";
import { useSession } from "../lib/session";
import { useConfirm } from "../components/ui/confirm-context";

export function Trash() {
  const { t, i18n } = useTranslation();
  const confirm = useConfirm();
  const { me } = useSession();
  const [items, setItems] = useState<TrashItem[] | null>(null);
  const [vehicleList, setVehicleList] = useState<Vehicle[]>([]);
  const [error, setError] = useState<Error | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const canRestore = me?.membership.role !== "reader";
  const canPurge = me?.membership.role === "owner";

  const load = () => {
    setError(null);
    Promise.all([trash.list(), vehicles.list()])
      .then(([loadedItems, loadedVehicles]) => {
        setItems(loadedItems);
        setVehicleList(loadedVehicles);
      })
      .catch(setError);
  };

  useEffect(load, []);

  const act = async (item: TrashItem, operation: () => Promise<unknown>) => {
    setActionError(null);
    setBusy(item.entity_id);
    try {
      await operation();
      load();
    } catch (cause) {
      setActionError(cause instanceof ApiError ? cause.message : t("common.error"));
    } finally {
      setBusy(null);
    }
  };

  if (error) return <ErrorState onRetry={load} />;
  if (!items) return <Skeleton lines={7} />;

  // A deleted vehicle is not in the vehicle list any more, so its records fall
  // back to a dash rather than showing a stale name.
  const vehicleName = (id: string | null) =>
    id ? (vehicleList.find((vehicle) => vehicle.id === id)?.name ?? "—") : "—";
  const when = (value: string) =>
    new Intl.DateTimeFormat(i18n.language, { dateStyle: "medium", timeStyle: "short" }).format(
      new Date(value),
    );

  return (
    <div className="space-y-5">
      <PageHeader title={t("trash.title")} description={t("trash.description")} />

      {actionError && (
        <p role="alert" className="rounded-lg bg-danger-soft px-4 py-3 text-sm text-danger">
          {actionError}
        </p>
      )}

      {items.length === 0 ? (
        <EmptyState title={t("trash.empty")} description={t("trash.emptyHint")} />
      ) : (
        <ul className="space-y-3">
          {items.map((item) => (
            <li
              key={`${item.entity_type}-${item.entity_id}`}
              className="flex flex-col gap-3 rounded-xl border border-line bg-raised p-4 sm:flex-row sm:items-center sm:justify-between"
            >
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge>{t(`trash.kinds.${item.entity_type}`)}</Badge>
                  <p className="truncate font-semibold text-ink">{item.summary}</p>
                </div>
                <p className="mt-1 text-sm text-ink-subtle">
                  {[
                    item.entity_type === "vehicle" ? null : vehicleName(item.vehicle_id),
                    when(item.deleted_at),
                    item.deleted_by_label || null,
                  ]
                    .filter(Boolean)
                    .join(" · ")}
                </p>
              </div>
              <div className="flex shrink-0 flex-wrap gap-2">
                {canRestore && (
                  <Button
                    size="sm"
                    variant="secondary"
                    disabled={busy === item.entity_id}
                    onClick={() =>
                      void act(item, () => trash.restore(item.entity_type, item.entity_id))
                    }
                  >
                    {t("trash.restore")}
                  </Button>
                )}
                {canPurge && (
                  <Button
                    size="sm"
                    variant="danger"
                    disabled={busy === item.entity_id}
                    onClick={async () => {
                      if (await confirm(t("trash.confirmPurge"))) {
                        void act(item, () => trash.purge(item.entity_type, item.entity_id));
                      }
                    }}
                  >
                    {t("trash.purge")}
                  </Button>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
