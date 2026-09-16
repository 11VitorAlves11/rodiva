import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Link, useSearchParams } from "react-router-dom";

import { vehicles as vehiclesApi } from "../lib/api";
import { ApiError } from "../lib/api/client";
import type { Vehicle } from "../lib/api/types";
import { ErrorState } from "../components/ui/ErrorState";
import { Skeleton } from "../components/ui/Skeleton";
import { useSession } from "../lib/session";

export function Garage() {
  const { t } = useTranslation();
  const { me } = useSession();
  const canManage = me?.membership.role === "owner" || me?.membership.role === "manager";
  const [vehicles, setVehicles] = useState<Vehicle[] | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [searchParams, setSearchParams] = useSearchParams();
  const [showForm, setShowForm] = useState(searchParams.get("new") === "1");

  const load = () => {
    setError(null);
    vehiclesApi.list().then(setVehicles).catch(setError);
  };

  useEffect(load, []);

  if (error) return <ErrorState onRetry={load} />;
  if (vehicles === null) return <Skeleton lines={4} />;

  return (
    <div className="space-y-6">
      <div className="flex flex-col items-stretch gap-3 sm:flex-row sm:items-center sm:justify-between">
        <h1 className="text-xl font-semibold text-graphite dark:text-cream">{t("garage.title")}</h1>
        {canManage && <button
          onClick={() => {
            setShowForm((value) => !value);
            setSearchParams({}, { replace: true });
          }}
          className="self-start rounded-md bg-copper px-3 py-2 text-sm font-medium text-white hover:bg-copper-dark"
        >
          {t("garage.add")}
        </button>}
      </div>

      {showForm && (
        <VehicleForm
          onCreated={(vehicle) => {
            setVehicles((current) => [...(current ?? []), vehicle]);
            setShowForm(false);
          }}
        />
      )}

      {vehicles.length === 0 ? (
        <p className="text-sm text-graphite/50 dark:text-cream/50">{t("garage.empty")}</p>
      ) : (
        <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {vehicles.map((vehicle) => (
            <li key={vehicle.id} className="overflow-hidden rounded-xl border border-graphite/10 bg-white shadow-sm dark:border-white/10 dark:bg-surface-dark-raised">
              {vehicle.photo_url && <img src={vehicle.photo_url} alt="" className="h-36 w-full object-cover" />}
              <div className="p-4">
              <Link to={`/vehicles/${vehicle.id}`} className="font-medium text-graphite hover:text-copper dark:text-cream">
                {vehicle.name}
              </Link>
              <p className="text-sm text-graphite/50 dark:text-cream/50">
                {[vehicle.make, vehicle.model, vehicle.year].filter(Boolean).join(" · ") || "—"}
              </p>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function VehicleForm({ onCreated }: { onCreated: (vehicle: Vehicle) => void }) {
  const { t } = useTranslation();
  const [name, setName] = useState("");
  const [make, setMake] = useState("");
  const [model, setModel] = useState("");
  const [year, setYear] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const vehicle = await vehiclesApi.create({
        name,
        make: make || undefined,
        model: model || undefined,
        year: year ? Number(year) : undefined,
      });
      onCreated(vehicle);
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : t("common.error"));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="grid gap-3 rounded-xl border border-graphite/10 bg-white p-4 shadow-sm dark:border-white/10 dark:bg-surface-dark-raised sm:grid-cols-2"
    >
      <label className="text-sm sm:col-span-2">
        <span className="mb-1 block font-medium text-graphite/70 dark:text-cream/70">{t("garage.name")}</span>
        <input
          required
          value={name}
          onChange={(event) => setName(event.target.value)}
          className="w-full rounded-md border border-graphite/15 px-3 py-2 dark:border-white/15 dark:bg-surface-dark"
        />
      </label>
      <label className="text-sm">
        <span className="mb-1 block font-medium text-graphite/70 dark:text-cream/70">{t("garage.make")}</span>
        <input
          value={make}
          onChange={(event) => setMake(event.target.value)}
          className="w-full rounded-md border border-graphite/15 px-3 py-2 dark:border-white/15 dark:bg-surface-dark"
        />
      </label>
      <label className="text-sm">
        <span className="mb-1 block font-medium text-graphite/70 dark:text-cream/70">{t("garage.model")}</span>
        <input
          value={model}
          onChange={(event) => setModel(event.target.value)}
          className="w-full rounded-md border border-graphite/15 px-3 py-2 dark:border-white/15 dark:bg-surface-dark"
        />
      </label>
      <label className="text-sm">
        <span className="mb-1 block font-medium text-graphite/70 dark:text-cream/70">{t("garage.year")}</span>
        <input
          type="number"
          inputMode="numeric"
          value={year}
          onChange={(event) => setYear(event.target.value)}
          className="w-full rounded-md border border-graphite/15 px-3 py-2 dark:border-white/15 dark:bg-surface-dark"
        />
      </label>
      {error && <p className="text-sm text-red-700 sm:col-span-2">{error}</p>}
      <button
        type="submit"
        disabled={submitting}
        className="rounded-md bg-copper px-4 py-2 text-sm font-medium text-white hover:bg-copper-dark disabled:opacity-60 sm:col-span-2"
      >
        {t("garage.save")}
      </button>
    </form>
  );
}
