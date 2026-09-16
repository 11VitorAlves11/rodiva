import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { useTranslation } from "react-i18next";
import {
  Link,
  useNavigate,
  useParams,
  useSearchParams,
} from "react-router-dom";
import { TrashIcon } from "@heroicons/react/24/outline";

import { ErrorState } from "../components/ui/ErrorState";
import { Skeleton } from "../components/ui/Skeleton";
import { ChargingSection } from "../components/vehicle/ChargingSection";
import { ExpensesSection } from "../components/vehicle/ExpensesSection";
import { DocumentsSection } from "../components/vehicle/DocumentsSection";
import { NotesSection } from "../components/vehicle/NotesSection";
import {
  attachments,
  expenses,
  fuel,
  notes,
  odometer,
  vehicles,
  workRecords,
} from "../lib/api";
import { ApiError } from "../lib/api/client";
import type {
  Attachment,
  ExpenseRecord,
  FuelRecord,
  Note,
  OdometerReading,
  Vehicle as VehicleType,
  WorkKind,
  WorkRecord,
} from "../lib/api/types";
import { useSession } from "../lib/session";

export function Vehicle() {
  const { vehicleId = "" } = useParams();
  const { t, i18n } = useTranslation();
  const { me } = useSession();
  const navigate = useNavigate();
  const canManage =
    me?.membership.role === "owner" || me?.membership.role === "manager";
  const [vehicle, setVehicle] = useState<VehicleType | null>(null);
  const [readings, setReadings] = useState<OdometerReading[] | null>(null);
  const [fuelRecords, setFuelRecords] = useState<FuelRecord[] | null>(null);
  const [work, setWork] = useState<WorkRecord[] | null>(null);
  const [expenseRecords, setExpenseRecords] = useState<ExpenseRecord[] | null>(
    null,
  );
  const [noteRecords, setNoteRecords] = useState<Note[] | null>(null);
  const [documents, setDocuments] = useState<Attachment[] | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [editingVehicle, setEditingVehicle] = useState(false);
  const [searchParams, setSearchParams] = useSearchParams();
  const requestedSection = searchParams.get("section");
  const activeSection =
    (
      ["odometer", "fuel", "charging", "work", "expenses", "notes", "documents"] as const
    ).find((item) => item === requestedSection) ?? "fuel";

  const load = () => {
    setError(null);
    Promise.all([
      vehicles.get(vehicleId),
      odometer.list(vehicleId),
      fuel.list(vehicleId),
      workRecords.list(vehicleId),
      expenses.list(vehicleId),
      notes.list(vehicleId),
      attachments.list(vehicleId),
    ])
      .then(
        ([
          loadedVehicle,
          loadedReadings,
          loadedFuelRecords,
          loadedWork,
          loadedExpenses,
          loadedNotes,
          loadedDocuments,
        ]) => {
          setVehicle(loadedVehicle);
          setReadings(loadedReadings);
          setFuelRecords(loadedFuelRecords);
          setWork(loadedWork);
          setExpenseRecords(loadedExpenses);
          setNoteRecords(loadedNotes);
          setDocuments(loadedDocuments);
        },
      )
      .catch(setError);
  };

  useEffect(load, [vehicleId]);

  if (error) return <ErrorState onRetry={load} />;
  if (
    !vehicle ||
    !readings ||
    !fuelRecords ||
    !work ||
    !expenseRecords ||
    !noteRecords ||
    !documents
  )
    return <Skeleton lines={6} />;

  const currentReading = readings.reduce<number | null>(
    (highest, item) =>
      highest === null || item.reading > highest ? item.reading : highest,
    null,
  );
  const formatDate = (value: string) =>
    new Intl.DateTimeFormat(i18n.language).format(
      new Date(`${value}T12:00:00`),
    );

  async function uploadPhoto(file: File) {
    const dataUrl = await new Promise<string>((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(String(reader.result));
      reader.onerror = () => reject(reader.error);
      reader.readAsDataURL(file);
    });
    try {
      setVehicle(
        await vehicles.uploadPhoto(vehicleId, {
          content_base64: dataUrl.split(",", 2)[1],
          content_type: file.type,
        }),
      );
    } catch (cause) {
      setError(cause instanceof Error ? cause : new Error(t("common.error")));
    }
  }

  return (
    <div className="space-y-6">
      <Link
        to="/garage"
        className="text-sm font-medium text-copper hover:text-copper-dark"
      >
        {t("vehicle.back")}
      </Link>
      <div className="flex flex-col items-stretch gap-4 sm:flex-row sm:flex-wrap sm:items-end sm:justify-between">
        <div className="flex min-w-0 items-center gap-4">
          {vehicle.photo_url && (
            <img
              src={vehicle.photo_url}
              alt=""
              className="h-20 w-28 rounded-lg object-cover"
            />
          )}
          <div>
            <p className="text-sm text-slate-500">
              {[vehicle.make, vehicle.model, vehicle.year]
                .filter(Boolean)
                .join(" · ")}
            </p>
            <h1 className="text-2xl font-semibold text-ink">
              {vehicle.name}
            </h1>
            {canManage && (
              <label className="mt-2 inline-block cursor-pointer text-sm font-medium text-copper">
                {vehicle.photo_url
                  ? t("vehicle.changePhoto")
                  : t("vehicle.addPhoto")}
                <input
                  type="file"
                  accept="image/jpeg,image/png,image/webp"
                  capture="environment"
                  className="sr-only"
                  onChange={(event) => {
                    const file = event.target.files?.[0];
                    if (file) void uploadPhoto(file);
                  }}
                />
              </label>
            )}
          </div>
        </div>
        <div className="flex flex-col items-stretch gap-2 sm:items-end">
          <div className="self-start rounded-lg bg-copper/10 px-4 py-3 text-left sm:self-auto sm:text-right">
            <p className="text-xs font-medium uppercase tracking-wide text-copper-dark">
              {t("vehicle.currentOdometer")}
            </p>
            <p className="text-xl font-semibold text-ink">
              {currentReading === null
                ? "—"
                : `${currentReading.toLocaleString(i18n.language)} ${vehicle.distance_unit}`}
            </p>
          </div>
          {canManage && (
            <button
              onClick={() => setEditingVehicle((value) => !value)}
              className="rounded-lg border border-line px-3 py-2 text-sm font-semibold"
            >
              {t("common.edit")}
            </button>
          )}
        </div>
      </div>

      {editingVehicle && (
        <VehicleEditForm
          vehicle={vehicle}
          onSaved={(updated) => {
            setVehicle(updated);
            setEditingVehicle(false);
          }}
          onDelete={async () => {
            if (!window.confirm(t("vehicle.confirmDelete"))) return;
            await vehicles.remove(vehicle.id);
            navigate("/garage");
          }}
        />
      )}

      <nav
        aria-label={t("vehicle.sections")}
        className="flex gap-1 overflow-x-auto rounded-xl bg-raised p-1 shadow-sm"
      >
        {(
          [
            "fuel",
            "charging",
            "odometer",
            "work",
            "expenses",
            "notes",
            "documents",
          ] as const
        ).map((section) => (
          <button
            key={section}
            onClick={() => setSearchParams({ section })}
            className={`whitespace-nowrap rounded-lg px-4 py-2 text-sm font-medium ${activeSection === section ? "bg-copper text-white" : "text-slate-600 hover:bg-slate-100"}`}
          >
            {t(`${section}.title`)}
          </button>
        ))}
      </nav>

      {activeSection === "charging" && <ChargingSection vehicleId={vehicleId} unit={vehicle.distance_unit} />}

      {activeSection === "odometer" && (
        <section className="space-y-4 rounded-xl border border-line bg-raised p-4 shadow-sm sm:p-6">
          <div className="flex flex-col items-stretch gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h2 className="text-lg font-semibold text-ink">
                {t("odometer.title")}
              </h2>
              <p className="text-sm text-slate-500">
                {t("odometer.description")}
              </p>
            </div>
            <button
              onClick={() => setShowForm((value) => !value)}
              className="self-start rounded-md bg-copper px-3 py-2 text-sm font-medium text-white hover:bg-copper-dark"
            >
              {t("odometer.add")}
            </button>
          </div>
          {showForm && (
            <OdometerForm
              vehicleId={vehicleId}
              unit={vehicle.distance_unit}
              onCreated={(reading) => {
                setReadings((current) => [reading, ...(current ?? [])]);
                setShowForm(false);
                load();
              }}
            />
          )}
          {readings.length === 0 ? (
            <p className="py-4 text-sm text-slate-500">{t("odometer.empty")}</p>
          ) : (
            <ul className="divide-y divide-slate-100">
              {readings.map((item) => (
                <li
                  key={item.id}
                  className="flex flex-col gap-2 py-3 sm:flex-row sm:items-center sm:justify-between sm:gap-4"
                >
                  <div>
                    <p className="font-medium text-ink">
                      {item.reading.toLocaleString(i18n.language)}{" "}
                      {vehicle.distance_unit}
                    </p>
                    <p className="text-sm text-slate-500">
                      {formatDate(item.recorded_on)}
                      {item.is_adjustment
                        ? ` · ${t("odometer.adjustment")}`
                        : ""}
                    </p>
                    {item.notes && (
                      <p className="mt-1 text-sm text-slate-600">
                        {item.notes}
                      </p>
                    )}
                  </div>
                  <div className="flex items-center gap-3">
                    <p className="text-sm text-slate-500">
                      {item.distance === null
                        ? "—"
                        : `+${item.distance.toLocaleString(i18n.language)} ${vehicle.distance_unit}`}
                    </p>
                    <button
                      onClick={() => {
                        if (window.confirm(t("common.confirmDelete")))
                          void odometer.remove(vehicleId, item.id).then(load);
                      }}
                      className="flex items-center gap-1 text-xs font-medium text-red-700"
                    >
                      <TrashIcon aria-hidden="true" className="h-3.5 w-3.5" />
                      {t("common.delete")}
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>
      )}

      {activeSection === "fuel" && (
        <FuelSection
          records={fuelRecords}
          vehicleId={vehicleId}
          currentReading={currentReading}
          onCreated={() => load()}
        />
      )}
      {activeSection === "work" && (
        <WorkSection
          records={work}
          vehicleId={vehicleId}
          currentReading={currentReading}
          onCreated={load}
        />
      )}
      {activeSection === "expenses" && (
        <ExpensesSection
          records={expenseRecords}
          vehicleId={vehicleId}
          onCreated={load}
        />
      )}
      {activeSection === "notes" && (
        <NotesSection
          records={noteRecords}
          vehicleId={vehicleId}
          onCreated={load}
        />
      )}
      {activeSection === "documents" && (
        <DocumentsSection
          records={documents}
          vehicleId={vehicleId}
          onCreated={load}
        />
      )}
    </div>
  );
}

function VehicleEditForm({
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
      {error && (
        <p role="alert" className="text-sm text-red-700 sm:col-span-2">
          {error}
        </p>
      )}
      <div className="flex flex-col-reverse gap-2 sm:col-span-2 sm:flex-row sm:justify-between">
        <button
          type="button"
          onClick={() => void onDelete()}
          className="rounded-lg border border-red-300 px-4 py-2.5 font-semibold text-red-700 dark:border-red-800 dark:text-red-300"
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

function WorkSection({
  records,
  vehicleId,
  currentReading,
  onCreated,
}: {
  records: WorkRecord[];
  vehicleId: string;
  currentReading: number | null;
  onCreated: () => void;
}) {
  const { t, i18n } = useTranslation();
  const [show, setShow] = useState(false);
  const [description, setDescription] = useState("");
  const [cost, setCost] = useState("");
  const [kind, setKind] = useState<WorkKind>("maintenance");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  async function submit(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    try {
      await workRecords.create(vehicleId, {
        recorded_on: new Date().toISOString().slice(0, 10),
        kind,
        description,
        total_cost: cost.replace(",", ".") || undefined,
        odometer_reading: currentReading ?? undefined,
      });
      setShow(false);
      setDescription("");
      setCost("");
      onCreated();
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : t("common.error"));
    } finally {
      setSaving(false);
    }
  }
  async function remove(id: string) {
    if (window.confirm(t("common.confirmDelete"))) {
      await workRecords.remove(vehicleId, id);
      onCreated();
    }
  }
  return (
    <section className="space-y-4 rounded-xl border border-line bg-raised p-4 shadow-sm sm:p-6">
      <div className="flex flex-col items-stretch gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-lg font-semibold text-ink">
            {t("work.title")}
          </h2>
          <p className="text-sm text-slate-500">{t("work.description")}</p>
        </div>
        <button
          onClick={() => setShow((value) => !value)}
          className="self-start rounded-md bg-copper px-3 py-2 text-sm font-medium text-white hover:bg-copper-dark"
        >
          {t("work.add")}
        </button>
      </div>
      {show && (
        <form
          onSubmit={submit}
          className="grid gap-3 rounded-lg bg-sunken p-4 sm:grid-cols-2"
        >
          <select
            value={kind}
            onChange={(event) => setKind(event.target.value as WorkKind)}
            className="rounded-md border border-line bg-raised px-3 py-2"
          >
            <option value="maintenance">{t("work.maintenance")}</option>
            <option value="repair">{t("work.repair")}</option>
            <option value="modification">{t("work.modification")}</option>
          </select>
          <input
            required
            placeholder={t("work.placeholder")}
            value={description}
            onChange={(event) => setDescription(event.target.value)}
            className="rounded-md border border-line bg-raised px-3 py-2"
          />
          <input
            inputMode="decimal"
            placeholder={t("work.cost")}
            value={cost}
            onChange={(event) => setCost(event.target.value)}
            className="rounded-md border border-line bg-raised px-3 py-2"
          />
          {error && <p className="text-sm text-red-700">{error}</p>}
          <button
            disabled={saving}
            className="rounded-md bg-copper px-4 py-2 text-sm font-medium text-white disabled:opacity-60"
          >
            {t("garage.save")}
          </button>
        </form>
      )}
      <ul className="divide-y divide-slate-100">
        {records.map((record) => (
          <li
            key={record.id}
            className="flex min-w-0 flex-col gap-2 py-3 sm:flex-row sm:justify-between sm:gap-4"
          >
            <div className="min-w-0">
              <p className="break-words font-medium text-ink">
                {record.description}
              </p>
              <p className="text-sm text-slate-500">
                {t(`work.${record.kind}`)}
                {record.supplier ? ` · ${record.supplier}` : ""}
              </p>
            </div>
            <div className="flex shrink-0 items-center gap-3">
              <p className="text-sm text-slate-500">
                {record.total_cost
                  ? Number(record.total_cost).toLocaleString(i18n.language, {
                      style: "currency",
                      currency: "EUR",
                    })
                  : "—"}
              </p>
              <button
                onClick={() => void remove(record.id)}
                className="flex items-center gap-1 text-xs font-medium text-red-700"
              >
                <TrashIcon aria-hidden="true" className="h-3.5 w-3.5" />
                {t("common.delete")}
              </button>
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}

function FuelSection({
  records,
  vehicleId,
  currentReading,
  onCreated,
}: {
  records: FuelRecord[];
  vehicleId: string;
  currentReading: number | null;
  onCreated: () => void;
}) {
  const { t, i18n } = useTranslation();
  const [showForm, setShowForm] = useState(false);
  const formatDate = (value: string) =>
    new Intl.DateTimeFormat(i18n.language).format(
      new Date(`${value}T12:00:00`),
    );

  return (
    <section className="space-y-4 rounded-xl border border-line bg-raised p-4 shadow-sm sm:p-6">
      <div className="flex flex-col items-stretch gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-lg font-semibold text-ink">
            {t("fuel.title")}
          </h2>
          <p className="text-sm text-slate-500">{t("fuel.description")}</p>
        </div>
        <button
          onClick={() => setShowForm((value) => !value)}
          className="self-start rounded-md bg-copper px-3 py-2 text-sm font-medium text-white hover:bg-copper-dark"
        >
          {t("fuel.add")}
        </button>
      </div>
      {showForm && (
        <FuelForm
          vehicleId={vehicleId}
          currentReading={currentReading}
          onCreated={() => {
            setShowForm(false);
            onCreated();
          }}
        />
      )}
      {records.length === 0 ? (
        <p className="py-4 text-sm text-slate-500">{t("fuel.empty")}</p>
      ) : (
        <ul className="divide-y divide-slate-100">
          {records.map((record) => (
            <li
              key={record.id}
              className="flex min-w-0 flex-col gap-2 py-3 sm:flex-row sm:items-center sm:justify-between sm:gap-4"
            >
              <div className="min-w-0">
                <p className="font-medium text-ink">
                  {Number(record.volume_litres).toLocaleString(i18n.language)} L
                  ·{" "}
                  {Number(record.total_price).toLocaleString(i18n.language, {
                    style: "currency",
                    currency: "EUR",
                  })}
                </p>
                <p className="break-words text-sm text-slate-500">
                  {formatDate(record.recorded_on)}
                  {record.station ? ` · ${record.station}` : ""}
                </p>
              </div>
              <div className="flex items-center gap-3">
                <p className="text-sm text-slate-500">
                  {record.consumption_l_per_100km
                    ? `${Number(record.consumption_l_per_100km).toLocaleString(i18n.language)} L/100 km`
                    : "—"}
                </p>
                <button
                  onClick={() => {
                    if (window.confirm(t("common.confirmDelete")))
                      void fuel.remove(vehicleId, record.id).then(onCreated);
                  }}
                  className="flex items-center gap-1 text-xs font-medium text-red-700"
                >
                  <TrashIcon aria-hidden="true" className="h-3.5 w-3.5" />
                  {t("common.delete")}
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function FuelForm({
  vehicleId,
  currentReading,
  onCreated,
}: {
  vehicleId: string;
  currentReading: number | null;
  onCreated: () => void;
}) {
  const { t } = useTranslation();
  const [recordedOn, setRecordedOn] = useState(
    new Date().toISOString().slice(0, 10),
  );
  const [odometerReading, setOdometerReading] = useState(
    currentReading?.toString() ?? "",
  );
  const [volume, setVolume] = useState("");
  const [totalPrice, setTotalPrice] = useState("");
  const [station, setStation] = useState("");
  const [fullTank, setFullTank] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const decimal = (value: string) => value.replace(",", ".");

  async function submit(event: FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await fuel.create(vehicleId, {
        recorded_on: recordedOn,
        odometer_reading: odometerReading ? Number(odometerReading) : undefined,
        volume_litres: decimal(volume),
        total_price: decimal(totalPrice),
        station: station || undefined,
        full_tank: fullTank,
      });
      onCreated();
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : t("common.error"));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form
      onSubmit={submit}
      className="grid gap-3 rounded-lg bg-sunken p-4 sm:grid-cols-2"
    >
      <label className="text-sm">
        <span className="mb-1 block font-medium text-ink-muted">
          {t("fuel.date")}
        </span>
        <input
          required
          type="date"
          value={recordedOn}
          onChange={(event) => setRecordedOn(event.target.value)}
          className="w-full rounded-md border border-line bg-raised px-3 py-2"
        />
      </label>
      <label className="text-sm">
        <span className="mb-1 block font-medium text-ink-muted">
          {t("fuel.odometer")}
        </span>
        <input
          min="0"
          inputMode="numeric"
          type="number"
          value={odometerReading}
          onChange={(event) => setOdometerReading(event.target.value)}
          className="w-full rounded-md border border-line bg-raised px-3 py-2"
        />
      </label>
      <label className="text-sm">
        <span className="mb-1 block font-medium text-ink-muted">
          {t("fuel.volume")}
        </span>
        <input
          required
          min="0.001"
          step="0.001"
          inputMode="decimal"
          type="text"
          value={volume}
          onChange={(event) => setVolume(event.target.value)}
          className="w-full rounded-md border border-line bg-raised px-3 py-2"
        />
      </label>
      <label className="text-sm">
        <span className="mb-1 block font-medium text-ink-muted">
          {t("fuel.total")}
        </span>
        <input
          required
          min="0"
          step="0.01"
          inputMode="decimal"
          type="text"
          value={totalPrice}
          onChange={(event) => setTotalPrice(event.target.value)}
          className="w-full rounded-md border border-line bg-raised px-3 py-2"
        />
      </label>
      <label className="text-sm sm:col-span-2">
        <span className="mb-1 block font-medium text-ink-muted">
          {t("fuel.station")}
        </span>
        <input
          value={station}
          onChange={(event) => setStation(event.target.value)}
          className="w-full rounded-md border border-line bg-raised px-3 py-2"
        />
      </label>
      <label className="flex items-center gap-2 text-sm text-ink-muted sm:col-span-2">
        <input
          type="checkbox"
          checked={fullTank}
          onChange={(event) => setFullTank(event.target.checked)}
        />
        {t("fuel.fullTank")}
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

function OdometerForm({
  vehicleId,
  unit,
  onCreated,
}: {
  vehicleId: string;
  unit: string;
  onCreated: (reading: OdometerReading) => void;
}) {
  const { t } = useTranslation();
  const [recordedOn, setRecordedOn] = useState(
    new Date().toISOString().slice(0, 10),
  );
  const [reading, setReading] = useState("");
  const [notes, setNotes] = useState("");
  const [adjustment, setAdjustment] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      onCreated(
        await odometer.create(vehicleId, {
          recorded_on: recordedOn,
          reading: Number(reading),
          notes: notes || undefined,
          is_adjustment: adjustment,
        }),
      );
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : t("common.error"));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form
      onSubmit={submit}
      className="grid gap-3 rounded-lg bg-sunken p-4 sm:grid-cols-2"
    >
      <label className="text-sm">
        <span className="mb-1 block font-medium text-ink-muted">
          {t("odometer.date")}
        </span>
        <input
          required
          type="date"
          value={recordedOn}
          onChange={(event) => setRecordedOn(event.target.value)}
          className="w-full rounded-md border border-line bg-raised px-3 py-2"
        />
      </label>
      <label className="text-sm">
        <span className="mb-1 block font-medium text-ink-muted">
          {t("odometer.reading", { unit })}
        </span>
        <input
          required
          min="0"
          step="1"
          inputMode="numeric"
          type="number"
          value={reading}
          onChange={(event) => setReading(event.target.value)}
          className="w-full rounded-md border border-line bg-raised px-3 py-2"
        />
      </label>
      <label className="text-sm sm:col-span-2">
        <span className="mb-1 block font-medium text-ink-muted">
          {t("odometer.notes")}
        </span>
        <input
          value={notes}
          onChange={(event) => setNotes(event.target.value)}
          className="w-full rounded-md border border-line bg-raised px-3 py-2"
        />
      </label>
      <label className="flex items-center gap-2 text-sm text-ink-muted sm:col-span-2">
        <input
          type="checkbox"
          checked={adjustment}
          onChange={(event) => setAdjustment(event.target.checked)}
        />
        {t("odometer.adjustmentCheck")}
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
