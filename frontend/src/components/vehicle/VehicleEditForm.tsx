import { useState } from "react";
import type { FormEvent } from "react";
import { useTranslation } from "react-i18next";

import { vehicles } from "../../lib/api";
import { ApiError } from "../../lib/api/client";
import type { EnergyType, Vehicle as VehicleType } from "../../lib/api/types";

const ENERGY_TYPES: EnergyType[] = [
  "petrol",
  "diesel",
  "electric",
  "hybrid",
  "plugin_hybrid",
  "lpg",
  "other",
];

const FIELD = "mt-1 w-full rounded-lg border px-3 py-2.5 bg-raised";
export function VehicleEditForm({
  vehicle,
  onSaved,
  onDelete,
}: {
  vehicle: VehicleType;
  onSaved: (vehicle: VehicleType) => void;
  onDelete: () => Promise<void>;
}) {
  const { t } = useTranslation();
  const [name, setName] = useState(vehicle.name);
  const [make, setMake] = useState(vehicle.make ?? "");
  const [model, setModel] = useState(vehicle.model ?? "");
  const [year, setYear] = useState(vehicle.year?.toString() ?? "");
  const [plate, setPlate] = useState(vehicle.license_plate ?? "");
  const [vin, setVin] = useState(vehicle.vin ?? "");
  const [unit, setUnit] = useState<"km" | "mi">(vehicle.distance_unit);
  const [status, setStatus] = useState(vehicle.status);
  const [energy, setEnergy] = useState<EnergyType>(vehicle.energy_type);
  const [initialOdometer, setInitialOdometer] = useState(
    vehicle.initial_odometer?.toString() ?? "",
  );
  const [offset, setOffset] = useState(vehicle.odometer_offset.toString());
  const [multiplier, setMultiplier] = useState(vehicle.odometer_multiplier);
  const [purchaseDate, setPurchaseDate] = useState(vehicle.purchase_date ?? "");
  const [purchasePrice, setPurchasePrice] = useState(vehicle.purchase_price ?? "");
  const [purchaseOdometer, setPurchaseOdometer] = useState(
    vehicle.purchase_odometer?.toString() ?? "",
  );
  const [saleDate, setSaleDate] = useState(vehicle.sale_date ?? "");
  const [salePrice, setSalePrice] = useState(vehicle.sale_price ?? "");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  async function submit(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    try {
      onSaved(
        await vehicles.update(vehicle.id, {
          name,
          make: make || null,
          model: model || null,
          year: year ? Number(year) : null,
          license_plate: plate || null,
          vin: vin || null,
          distance_unit: unit,
          status,
          energy_type: energy,
          initial_odometer: initialOdometer ? Number(initialOdometer) : null,
          odometer_offset: Number(offset) || 0,
          // Comma is how a decimal is typed in pt-PT; the API takes a point.
          odometer_multiplier: multiplier.replace(",", ".") || "1.0",
          purchase_date: purchaseDate || null,
          purchase_price: purchasePrice ? purchasePrice.replace(",", ".") : null,
          purchase_odometer: purchaseOdometer ? Number(purchaseOdometer) : null,
          sale_date: saleDate || null,
          sale_price: salePrice ? salePrice.replace(",", ".") : null,
        }),
      );
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : t("common.error"));
    } finally {
      setSaving(false);
    }
  }
  return (
    <form
      onSubmit={submit}
      className="grid min-w-0 gap-3 rounded-xl border border-copper/20 bg-raised p-4 dark:border-white/10 sm:grid-cols-2"
    >
      <label className="text-sm sm:col-span-2">
        {t("garage.name")}
        <input
          required
          value={name}
          onChange={(event) => setName(event.target.value)}
          className="mt-1 w-full rounded-lg border px-3 py-2.5 bg-raised"
        />
      </label>
      <label className="text-sm">
        {t("garage.make")}
        <input
          value={make}
          onChange={(event) => setMake(event.target.value)}
          className="mt-1 w-full rounded-lg border px-3 py-2.5 bg-raised"
        />
      </label>
      <label className="text-sm">
        {t("garage.model")}
        <input
          value={model}
          onChange={(event) => setModel(event.target.value)}
          className="mt-1 w-full rounded-lg border px-3 py-2.5 bg-raised"
        />
      </label>
      <label className="text-sm">
        {t("garage.year")}
        <input
          type="number"
          inputMode="numeric"
          value={year}
          onChange={(event) => setYear(event.target.value)}
          className="mt-1 w-full rounded-lg border px-3 py-2.5 bg-raised"
        />
      </label>
      <label className="text-sm">
        {t("vehicle.licensePlate")}
        <input
          value={plate}
          onChange={(event) => setPlate(event.target.value)}
          className="mt-1 w-full rounded-lg border px-3 py-2.5 bg-raised"
        />
      </label>
      <label className="text-sm">
        VIN
        <input
          value={vin}
          onChange={(event) => setVin(event.target.value)}
          className="mt-1 w-full rounded-lg border px-3 py-2.5 bg-raised"
        />
      </label>
      <label className="text-sm">
        {t("vehicle.distanceUnit")}
        <select
          value={unit}
          onChange={(event) => setUnit(event.target.value as "km" | "mi")}
          className="mt-1 w-full rounded-lg border px-3 py-2.5 bg-raised"
        >
          <option value="km">km</option>
          <option value="mi">mi</option>
        </select>
      </label>
      <label className="text-sm sm:col-span-2">
        {t("vehicle.status")}
        <select
          value={status}
          onChange={(event) =>
            setStatus(event.target.value as VehicleType["status"])
          }
          className="mt-1 w-full rounded-lg border px-3 py-2.5 bg-raised"
        >
          {(["active", "parked", "sold", "archived"] as const).map((value) => (
            <option key={value} value={value}>
              {t(`vehicle.statuses.${value}`)}
            </option>
          ))}
        </select>
      </label>
      <label className="text-sm">
        {t("vehicle.energyType")}
        <select
          value={energy}
          onChange={(event) => setEnergy(event.target.value as EnergyType)}
          className={FIELD}
        >
          {ENERGY_TYPES.map((value) => (
            <option key={value} value={value}>
              {t(`vehicle.energyTypes.${value}`)}
            </option>
          ))}
        </select>
      </label>
      <label className="text-sm">
        {t("vehicle.initialOdometer")}
        <input
          type="number"
          inputMode="numeric"
          value={initialOdometer}
          onChange={(event) => setInitialOdometer(event.target.value)}
          className={FIELD}
        />
      </label>

      <fieldset className="rounded-lg border border-line p-3 sm:col-span-2">
        <legend className="px-1 text-sm font-medium">{t("vehicle.odometerCorrection")}</legend>
        <p className="mb-2 text-xs text-ink-subtle">{t("vehicle.odometerCorrectionHint")}</p>
        <div className="grid gap-3 sm:grid-cols-2">
          <label className="text-sm">
            {t("vehicle.odometerOffset")}
            <input
              type="number"
              inputMode="numeric"
              value={offset}
              onChange={(event) => setOffset(event.target.value)}
              className={FIELD}
            />
          </label>
          <label className="text-sm">
            {t("vehicle.odometerMultiplier")}
            <input
              inputMode="decimal"
              value={multiplier}
              onChange={(event) => setMultiplier(event.target.value)}
              className={FIELD}
            />
          </label>
        </div>
      </fieldset>

      <fieldset className="rounded-lg border border-line p-3 sm:col-span-2">
        <legend className="px-1 text-sm font-medium">{t("vehicle.ownership")}</legend>
        <div className="grid gap-3 sm:grid-cols-3">
          <label className="text-sm">
            {t("vehicle.purchaseDate")}
            <input
              type="date"
              value={purchaseDate}
              onChange={(event) => setPurchaseDate(event.target.value)}
              className={FIELD}
            />
          </label>
          <label className="text-sm">
            {t("vehicle.purchasePrice")}
            <input
              inputMode="decimal"
              value={purchasePrice}
              onChange={(event) => setPurchasePrice(event.target.value)}
              className={FIELD}
            />
          </label>
          <label className="text-sm">
            {t("vehicle.purchaseOdometer")}
            <input
              type="number"
              inputMode="numeric"
              value={purchaseOdometer}
              onChange={(event) => setPurchaseOdometer(event.target.value)}
              className={FIELD}
            />
          </label>
          <label className="text-sm">
            {t("vehicle.saleDate")}
            <input
              type="date"
              value={saleDate}
              onChange={(event) => setSaleDate(event.target.value)}
              className={FIELD}
            />
          </label>
          <label className="text-sm">
            {t("vehicle.salePrice")}
            <input
              inputMode="decimal"
              value={salePrice}
              onChange={(event) => setSalePrice(event.target.value)}
              className={FIELD}
            />
          </label>
        </div>
      </fieldset>

      {error && (
        <p role="alert" className="text-sm text-danger sm:col-span-2">
          {error}
        </p>
      )}
      <div className="flex flex-col-reverse gap-2 sm:col-span-2 sm:flex-row sm:justify-between">
        <button
          type="button"
          onClick={() => void onDelete()}
          className="rounded-lg border border-danger/40 px-4 py-2.5 font-semibold text-danger"
        >
          {t("vehicle.delete")}
        </button>
        <button
          disabled={saving}
          className="rounded-lg bg-copper px-4 py-2.5 font-semibold text-white disabled:opacity-50"
        >
          {t("common.saveChanges")}
        </button>
      </div>
    </form>
  );
}
