import { useEffect, useState } from "react";
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
import { VehicleEditForm } from "../components/vehicle/VehicleEditForm";
import { TagPicker } from "../components/tags/TagPicker";
import { WorkSection } from "../components/vehicle/WorkSection";
import { FuelSection } from "../components/vehicle/FuelSection";
import { OdometerForm } from "../components/vehicle/OdometerForm";
import {
  attachments,
  expenses,
  fuel,
  notes,
  odometer,
  vehicles,
  workRecords,
} from "../lib/api";
import type {
  Attachment,
  ExpenseRecord,
  FuelRecord,
  Note,
  OdometerReading,
  Vehicle as VehicleType,
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
  const canEdit = canManage || me?.membership.role === "editor";
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
            <p className="text-sm text-ink-subtle">
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
        <TagPicker kind="vehicle" recordId={vehicle.id} canEdit={canEdit} className="mt-4" />
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

      {/* Scrolls sideways on a phone; wraps on wider screens so the last tab is
          not sliced mid-word against the container edge. */}
      <nav
        aria-label={t("vehicle.sections")}
        className="flex gap-1 overflow-x-auto rounded-xl bg-raised p-1 shadow-sm md:flex-wrap md:overflow-x-visible"
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
            className={`whitespace-nowrap rounded-lg px-4 py-2 text-sm font-medium ${activeSection === section ? "bg-copper text-white" : "text-ink-subtle hover:bg-sunken"}`}
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
              <p className="text-sm text-ink-subtle">
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
            <p className="py-4 text-sm text-ink-subtle">{t("odometer.empty")}</p>
          ) : (
            <ul className="divide-y divide-line">
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
                    <p className="text-sm text-ink-subtle">
                      {formatDate(item.recorded_on)}
                      {item.is_adjustment
                        ? ` · ${t("odometer.adjustment")}`
                        : ""}
                    </p>
                    {item.notes && (
                      <p className="mt-1 text-sm text-ink-subtle">
                        {item.notes}
                      </p>
                    )}
                  </div>
                  <div className="flex items-center gap-3">
                    <p className="text-sm text-ink-subtle">
                      {item.distance === null
                        ? "—"
                        : `+${item.distance.toLocaleString(i18n.language)} ${vehicle.distance_unit}`}
                    </p>
                    <button
                      onClick={() => {
                        if (window.confirm(t("common.confirmDelete")))
                          void odometer.remove(vehicleId, item.id).then(load);
                      }}
                      className="flex items-center gap-1 text-xs font-medium text-danger"
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
