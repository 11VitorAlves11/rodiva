import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { vehicles as vehiclesApi } from "../lib/api";
import { ApiError } from "../lib/api/client";
import type { Vehicle } from "../lib/api/types";
import { ErrorState } from "../components/ui/ErrorState";
import { Skeleton } from "../components/ui/Skeleton";

export function Garage() {
  const { t } = useTranslation();
  const [vehicles, setVehicles] = useState<Vehicle[] | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [showForm, setShowForm] = useState(false);

  const load = () => {
    setError(null);
    vehiclesApi.list().then(setVehicles).catch(setError);
  };

  useEffect(load, []);

  if (error) return <ErrorState onRetry={load} />;
  if (vehicles === null) return <Skeleton lines={4} />;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-slate-900">{t("garage.title")}</h1>
        <button
          onClick={() => setShowForm((value) => !value)}
          className="rounded-md bg-[#B94A22] px-3 py-2 text-sm font-medium text-white hover:bg-[#9E3E1D]"
        >
          {t("garage.add")}
        </button>
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
        <p className="text-sm text-slate-500">{t("garage.empty")}</p>
      ) : (
        <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {vehicles.map((vehicle) => (
            <li key={vehicle.id} className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
              {vehicle.photo_url && <img src={vehicle.photo_url} alt="" className="h-36 w-full object-cover" />}
              <div className="p-4">
              <Link to={`/vehicles/${vehicle.id}`} className="font-medium text-slate-900 hover:text-[#B94A22]">
                {vehicle.name}
              </Link>
              <p className="text-sm text-slate-500">
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
      className="grid gap-3 rounded-lg border border-slate-200 bg-white p-4 shadow-sm sm:grid-cols-2"
    >
      <label className="text-sm sm:col-span-2">
        <span className="mb-1 block font-medium text-slate-700">{t("garage.name")}</span>
        <input
          required
          value={name}
          onChange={(event) => setName(event.target.value)}
          className="w-full rounded-md border border-slate-300 px-3 py-2"
        />
      </label>
      <label className="text-sm">
        <span className="mb-1 block font-medium text-slate-700">{t("garage.make")}</span>
        <input
          value={make}
          onChange={(event) => setMake(event.target.value)}
          className="w-full rounded-md border border-slate-300 px-3 py-2"
        />
      </label>
      <label className="text-sm">
        <span className="mb-1 block font-medium text-slate-700">{t("garage.model")}</span>
        <input
          value={model}
          onChange={(event) => setModel(event.target.value)}
          className="w-full rounded-md border border-slate-300 px-3 py-2"
        />
      </label>
      <label className="text-sm">
        <span className="mb-1 block font-medium text-slate-700">{t("garage.year")}</span>
        <input
          type="number"
          inputMode="numeric"
          value={year}
          onChange={(event) => setYear(event.target.value)}
          className="w-full rounded-md border border-slate-300 px-3 py-2"
        />
      </label>
      {error && <p className="text-sm text-red-700 sm:col-span-2">{error}</p>}
      <button
        type="submit"
        disabled={submitting}
        className="rounded-md bg-[#B94A22] px-4 py-2 text-sm font-medium text-white hover:bg-[#9E3E1D] disabled:opacity-60 sm:col-span-2"
      >
        {t("garage.save")}
      </button>
    </form>
  );
}
