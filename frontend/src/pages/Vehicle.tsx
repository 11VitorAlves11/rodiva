import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Link, useParams, useSearchParams } from "react-router-dom";

import { ErrorState } from "../components/ui/ErrorState";
import { Skeleton } from "../components/ui/Skeleton";
import { ExpensesSection } from "../components/vehicle/ExpensesSection";
import { DocumentsSection } from "../components/vehicle/DocumentsSection";
import { NotesSection } from "../components/vehicle/NotesSection";
import { attachments, expenses, fuel, notes, odometer, vehicles, workRecords } from "../lib/api";
import { ApiError } from "../lib/api/client";
import type { Attachment, ExpenseRecord, FuelRecord, Note, OdometerReading, Vehicle as VehicleType, WorkKind, WorkRecord } from "../lib/api/types";

export function Vehicle() {
  const { vehicleId = "" } = useParams();
  const { t, i18n } = useTranslation();
  const [vehicle, setVehicle] = useState<VehicleType | null>(null);
  const [readings, setReadings] = useState<OdometerReading[] | null>(null);
  const [fuelRecords, setFuelRecords] = useState<FuelRecord[] | null>(null);
  const [work, setWork] = useState<WorkRecord[] | null>(null);
  const [expenseRecords, setExpenseRecords] = useState<ExpenseRecord[] | null>(null);
  const [noteRecords, setNoteRecords] = useState<Note[] | null>(null);
  const [documents, setDocuments] = useState<Attachment[] | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [searchParams, setSearchParams] = useSearchParams();
  const requestedSection = searchParams.get("section");
  const activeSection = (["odometer", "fuel", "work", "expenses", "notes", "documents"] as const).find((item) => item === requestedSection) ?? "fuel";

  const load = () => {
    setError(null);
    Promise.all([vehicles.get(vehicleId), odometer.list(vehicleId), fuel.list(vehicleId), workRecords.list(vehicleId), expenses.list(vehicleId), notes.list(vehicleId), attachments.list(vehicleId)])
      .then(([loadedVehicle, loadedReadings, loadedFuelRecords, loadedWork, loadedExpenses, loadedNotes, loadedDocuments]) => {
        setVehicle(loadedVehicle);
        setReadings(loadedReadings);
        setFuelRecords(loadedFuelRecords);
        setWork(loadedWork);
        setExpenseRecords(loadedExpenses);
        setNoteRecords(loadedNotes);
        setDocuments(loadedDocuments);
      })
      .catch(setError);
  };

  useEffect(load, [vehicleId]);

  if (error) return <ErrorState onRetry={load} />;
  if (!vehicle || !readings || !fuelRecords || !work || !expenseRecords || !noteRecords || !documents) return <Skeleton lines={6} />;

  const currentReading = readings.reduce<number | null>(
    (highest, item) => (highest === null || item.reading > highest ? item.reading : highest),
    null,
  );
  const formatDate = (value: string) => new Intl.DateTimeFormat(i18n.language).format(new Date(`${value}T12:00:00`));

  async function uploadPhoto(file: File) {
    const dataUrl = await new Promise<string>((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(String(reader.result));
      reader.onerror = () => reject(reader.error);
      reader.readAsDataURL(file);
    });
    try {
      setVehicle(await vehicles.uploadPhoto(vehicleId, {
        content_base64: dataUrl.split(",", 2)[1],
        content_type: file.type,
      }));
    } catch (cause) {
      setError(cause instanceof Error ? cause : new Error(t("common.error")));
    }
  }

  return (
    <div className="space-y-6">
      <Link to="/garage" className="text-sm font-medium text-copper hover:text-copper-dark">{t("vehicle.back")}</Link>
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div className="flex items-center gap-4">
          {vehicle.photo_url && <img src={vehicle.photo_url} alt="" className="h-20 w-28 rounded-lg object-cover" />}
          <div>
          <p className="text-sm text-slate-500">{[vehicle.make, vehicle.model, vehicle.year].filter(Boolean).join(" · ")}</p>
          <h1 className="text-2xl font-semibold text-slate-900">{vehicle.name}</h1>
          <label className="mt-2 inline-block cursor-pointer text-sm font-medium text-copper">{vehicle.photo_url ? t("vehicle.changePhoto") : t("vehicle.addPhoto")}<input type="file" accept="image/jpeg,image/png,image/webp" className="sr-only" onChange={(event) => { const file = event.target.files?.[0]; if (file) void uploadPhoto(file); }} /></label>
          </div>
        </div>
        <div className="rounded-lg bg-copper/10 px-4 py-3 text-right">
          <p className="text-xs font-medium uppercase tracking-wide text-copper-dark">{t("vehicle.currentOdometer")}</p>
          <p className="text-xl font-semibold text-slate-900">{currentReading === null ? "—" : `${currentReading.toLocaleString(i18n.language)} ${vehicle.distance_unit}`}</p>
        </div>
      </div>

      <nav aria-label={t("vehicle.sections")} className="flex gap-1 overflow-x-auto rounded-xl bg-white p-1 shadow-sm">
        {(["fuel", "odometer", "work", "expenses", "notes", "documents"] as const).map((section) => (
          <button
            key={section}
            onClick={() => setSearchParams({ section })}
            className={`whitespace-nowrap rounded-lg px-4 py-2 text-sm font-medium ${activeSection === section ? "bg-copper text-white" : "text-slate-600 hover:bg-slate-100"}`}
          >
            {t(`${section}.title`)}
          </button>
        ))}
      </nav>

      {activeSection === "odometer" && <section className="space-y-4 rounded-xl border border-slate-200 bg-white p-4 shadow-sm sm:p-6">
        <div className="flex items-center justify-between gap-4">
          <div>
            <h2 className="text-lg font-semibold text-slate-900">{t("odometer.title")}</h2>
            <p className="text-sm text-slate-500">{t("odometer.description")}</p>
          </div>
          <button onClick={() => setShowForm((value) => !value)} className="rounded-md bg-copper px-3 py-2 text-sm font-medium text-white hover:bg-copper-dark">
            {t("odometer.add")}
          </button>
        </div>
        {showForm && <OdometerForm vehicleId={vehicleId} unit={vehicle.distance_unit} onCreated={(reading) => {
          setReadings((current) => [reading, ...(current ?? [])]);
          setShowForm(false);
          load();
        }} />}
        {readings.length === 0 ? <p className="py-4 text-sm text-slate-500">{t("odometer.empty")}</p> : (
          <ul className="divide-y divide-slate-100">
            {readings.map((item) => <li key={item.id} className="flex items-center justify-between gap-4 py-3">
              <div>
                <p className="font-medium text-slate-900">{item.reading.toLocaleString(i18n.language)} {vehicle.distance_unit}</p>
                <p className="text-sm text-slate-500">{formatDate(item.recorded_on)}{item.is_adjustment ? ` · ${t("odometer.adjustment")}` : ""}</p>
                {item.notes && <p className="mt-1 text-sm text-slate-600">{item.notes}</p>}
              </div>
              <div className="flex items-center gap-3">
                <p className="text-sm text-slate-500">{item.distance === null ? "—" : `+${item.distance.toLocaleString(i18n.language)} ${vehicle.distance_unit}`}</p>
                <button
                  onClick={() => { if (window.confirm(t("common.confirmDelete"))) void odometer.remove(vehicleId, item.id).then(load); }}
                  className="text-xs font-medium text-red-700"
                >
                  {t("common.delete")}
                </button>
              </div>
            </li>)}
          </ul>
        )}
      </section>}

      {activeSection === "fuel" && <FuelSection
        records={fuelRecords}
        vehicleId={vehicleId}
        currentReading={currentReading}
        onCreated={() => load()}
      />}
      {activeSection === "work" && <WorkSection records={work} vehicleId={vehicleId} currentReading={currentReading} onCreated={load} />}
      {activeSection === "expenses" && <ExpensesSection records={expenseRecords} vehicleId={vehicleId} onCreated={load} />}
      {activeSection === "notes" && <NotesSection records={noteRecords} vehicleId={vehicleId} onCreated={load} />}
      {activeSection === "documents" && <DocumentsSection records={documents} vehicleId={vehicleId} onCreated={load} />}
    </div>
  );
}

function WorkSection({ records, vehicleId, currentReading, onCreated }: { records: WorkRecord[]; vehicleId: string; currentReading: number | null; onCreated: () => void }) {
  const { t, i18n } = useTranslation(); const [show, setShow] = useState(false); const [description, setDescription] = useState(""); const [cost, setCost] = useState(""); const [kind, setKind] = useState<WorkKind>("maintenance"); const [saving, setSaving] = useState(false); const [error, setError] = useState<string | null>(null);
  async function submit(event: FormEvent) { event.preventDefault(); setSaving(true); setError(null); try { await workRecords.create(vehicleId, { recorded_on: new Date().toISOString().slice(0, 10), kind, description, total_cost: cost.replace(",", ".") || undefined, odometer_reading: currentReading ?? undefined }); setShow(false); setDescription(""); setCost(""); onCreated(); } catch (cause) { setError(cause instanceof ApiError ? cause.message : t("common.error")); } finally { setSaving(false); } }
  async function remove(id: string) { if (window.confirm(t("common.confirmDelete"))) { await workRecords.remove(vehicleId, id); onCreated(); } }
  return <section className="space-y-4 rounded-xl border border-slate-200 bg-white p-4 shadow-sm sm:p-6"><div className="flex items-center justify-between gap-4"><div><h2 className="text-lg font-semibold text-slate-900">{t("work.title")}</h2><p className="text-sm text-slate-500">{t("work.description")}</p></div><button onClick={() => setShow((value) => !value)} className="rounded-md bg-copper px-3 py-2 text-sm font-medium text-white hover:bg-copper-dark">{t("work.add")}</button></div>{show && <form onSubmit={submit} className="grid gap-3 rounded-lg bg-slate-50 p-4 sm:grid-cols-2"><select value={kind} onChange={(event) => setKind(event.target.value as WorkKind)} className="rounded-md border border-slate-300 bg-white px-3 py-2"><option value="maintenance">{t("work.maintenance")}</option><option value="repair">{t("work.repair")}</option><option value="modification">{t("work.modification")}</option></select><input required placeholder={t("work.placeholder")} value={description} onChange={(event) => setDescription(event.target.value)} className="rounded-md border border-slate-300 bg-white px-3 py-2" /><input inputMode="decimal" placeholder={t("work.cost")} value={cost} onChange={(event) => setCost(event.target.value)} className="rounded-md border border-slate-300 bg-white px-3 py-2" />{error && <p className="text-sm text-red-700">{error}</p>}<button disabled={saving} className="rounded-md bg-copper px-4 py-2 text-sm font-medium text-white disabled:opacity-60">{t("garage.save")}</button></form>}<ul className="divide-y divide-slate-100">{records.map((record) => <li key={record.id} className="flex justify-between gap-4 py-3"><div><p className="font-medium text-slate-900">{record.description}</p><p className="text-sm text-slate-500">{t(`work.${record.kind}`)}{record.supplier ? ` · ${record.supplier}` : ""}</p></div><div className="flex items-center gap-3"><p className="text-sm text-slate-500">{record.total_cost ? Number(record.total_cost).toLocaleString(i18n.language, { style: "currency", currency: "EUR" }) : "—"}</p><button onClick={() => void remove(record.id)} className="text-xs font-medium text-red-700">{t("common.delete")}</button></div></li>)}</ul></section>;
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
  const formatDate = (value: string) => new Intl.DateTimeFormat(i18n.language).format(new Date(`${value}T12:00:00`));

  return <section className="space-y-4 rounded-xl border border-slate-200 bg-white p-4 shadow-sm sm:p-6">
    <div className="flex items-center justify-between gap-4">
      <div><h2 className="text-lg font-semibold text-slate-900">{t("fuel.title")}</h2><p className="text-sm text-slate-500">{t("fuel.description")}</p></div>
      <button onClick={() => setShowForm((value) => !value)} className="rounded-md bg-copper px-3 py-2 text-sm font-medium text-white hover:bg-copper-dark">{t("fuel.add")}</button>
    </div>
    {showForm && <FuelForm vehicleId={vehicleId} currentReading={currentReading} onCreated={() => { setShowForm(false); onCreated(); }} />}
    {records.length === 0 ? <p className="py-4 text-sm text-slate-500">{t("fuel.empty")}</p> : <ul className="divide-y divide-slate-100">
      {records.map((record) => <li key={record.id} className="flex items-center justify-between gap-4 py-3">
        <div><p className="font-medium text-slate-900">{Number(record.volume_litres).toLocaleString(i18n.language)} L · {Number(record.total_price).toLocaleString(i18n.language, { style: "currency", currency: "EUR" })}</p><p className="text-sm text-slate-500">{formatDate(record.recorded_on)}{record.station ? ` · ${record.station}` : ""}</p></div>
        <div className="flex items-center gap-3">
          <p className="text-sm text-slate-500">{record.consumption_l_per_100km ? `${Number(record.consumption_l_per_100km).toLocaleString(i18n.language)} L/100 km` : "—"}</p>
          <button
            onClick={() => { if (window.confirm(t("common.confirmDelete"))) void fuel.remove(vehicleId, record.id).then(onCreated); }}
            className="text-xs font-medium text-red-700"
          >
            {t("common.delete")}
          </button>
        </div>
      </li>)}
    </ul>}
  </section>;
}

function FuelForm({ vehicleId, currentReading, onCreated }: { vehicleId: string; currentReading: number | null; onCreated: () => void }) {
  const { t } = useTranslation();
  const [recordedOn, setRecordedOn] = useState(new Date().toISOString().slice(0, 10));
  const [odometerReading, setOdometerReading] = useState(currentReading?.toString() ?? "");
  const [volume, setVolume] = useState("");
  const [totalPrice, setTotalPrice] = useState("");
  const [station, setStation] = useState("");
  const [fullTank, setFullTank] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const decimal = (value: string) => value.replace(",", ".");

  async function submit(event: FormEvent) {
    event.preventDefault(); setSubmitting(true); setError(null);
    try {
      await fuel.create(vehicleId, { recorded_on: recordedOn, odometer_reading: odometerReading ? Number(odometerReading) : undefined, volume_litres: decimal(volume), total_price: decimal(totalPrice), station: station || undefined, full_tank: fullTank });
      onCreated();
    } catch (cause) { setError(cause instanceof ApiError ? cause.message : t("common.error")); } finally { setSubmitting(false); }
  }

  return <form onSubmit={submit} className="grid gap-3 rounded-lg bg-slate-50 p-4 sm:grid-cols-2">
    <label className="text-sm"><span className="mb-1 block font-medium text-slate-700">{t("fuel.date")}</span><input required type="date" value={recordedOn} onChange={(event) => setRecordedOn(event.target.value)} className="w-full rounded-md border border-slate-300 bg-white px-3 py-2" /></label>
    <label className="text-sm"><span className="mb-1 block font-medium text-slate-700">{t("fuel.odometer")}</span><input min="0" inputMode="numeric" type="number" value={odometerReading} onChange={(event) => setOdometerReading(event.target.value)} className="w-full rounded-md border border-slate-300 bg-white px-3 py-2" /></label>
    <label className="text-sm"><span className="mb-1 block font-medium text-slate-700">{t("fuel.volume")}</span><input required min="0.001" step="0.001" inputMode="decimal" type="text" value={volume} onChange={(event) => setVolume(event.target.value)} className="w-full rounded-md border border-slate-300 bg-white px-3 py-2" /></label>
    <label className="text-sm"><span className="mb-1 block font-medium text-slate-700">{t("fuel.total")}</span><input required min="0" step="0.01" inputMode="decimal" type="text" value={totalPrice} onChange={(event) => setTotalPrice(event.target.value)} className="w-full rounded-md border border-slate-300 bg-white px-3 py-2" /></label>
    <label className="text-sm sm:col-span-2"><span className="mb-1 block font-medium text-slate-700">{t("fuel.station")}</span><input value={station} onChange={(event) => setStation(event.target.value)} className="w-full rounded-md border border-slate-300 bg-white px-3 py-2" /></label>
    <label className="flex items-center gap-2 text-sm text-slate-700 sm:col-span-2"><input type="checkbox" checked={fullTank} onChange={(event) => setFullTank(event.target.checked)} />{t("fuel.fullTank")}</label>
    {error && <p className="text-sm text-red-700 sm:col-span-2">{error}</p>}
    <button type="submit" disabled={submitting} className="rounded-md bg-copper px-4 py-2 text-sm font-medium text-white hover:bg-copper-dark disabled:opacity-60 sm:col-span-2">{t("garage.save")}</button>
  </form>;
}

function OdometerForm({ vehicleId, unit, onCreated }: { vehicleId: string; unit: string; onCreated: (reading: OdometerReading) => void }) {
  const { t } = useTranslation();
  const [recordedOn, setRecordedOn] = useState(new Date().toISOString().slice(0, 10));
  const [reading, setReading] = useState("");
  const [notes, setNotes] = useState("");
  const [adjustment, setAdjustment] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setSubmitting(true); setError(null);
    try {
      onCreated(await odometer.create(vehicleId, { recorded_on: recordedOn, reading: Number(reading), notes: notes || undefined, is_adjustment: adjustment }));
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : t("common.error"));
    } finally { setSubmitting(false); }
  }

  return <form onSubmit={submit} className="grid gap-3 rounded-lg bg-slate-50 p-4 sm:grid-cols-2">
    <label className="text-sm"><span className="mb-1 block font-medium text-slate-700">{t("odometer.date")}</span><input required type="date" value={recordedOn} onChange={(event) => setRecordedOn(event.target.value)} className="w-full rounded-md border border-slate-300 bg-white px-3 py-2" /></label>
    <label className="text-sm"><span className="mb-1 block font-medium text-slate-700">{t("odometer.reading", { unit })}</span><input required min="0" step="1" inputMode="numeric" type="number" value={reading} onChange={(event) => setReading(event.target.value)} className="w-full rounded-md border border-slate-300 bg-white px-3 py-2" /></label>
    <label className="text-sm sm:col-span-2"><span className="mb-1 block font-medium text-slate-700">{t("odometer.notes")}</span><input value={notes} onChange={(event) => setNotes(event.target.value)} className="w-full rounded-md border border-slate-300 bg-white px-3 py-2" /></label>
    <label className="flex items-center gap-2 text-sm text-slate-700 sm:col-span-2"><input type="checkbox" checked={adjustment} onChange={(event) => setAdjustment(event.target.checked)} />{t("odometer.adjustmentCheck")}</label>
    {error && <p className="text-sm text-red-700 sm:col-span-2">{error}</p>}
    <button type="submit" disabled={submitting} className="rounded-md bg-copper px-4 py-2 text-sm font-medium text-white hover:bg-copper-dark disabled:opacity-60 sm:col-span-2">{t("garage.save")}</button>
  </form>;
}
