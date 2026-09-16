import { useEffect, useMemo, useState } from "react";
import type { FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { PlusIcon, TrashIcon } from "@heroicons/react/24/outline";
import { XMarkIcon } from "@heroicons/react/20/solid";

import { ErrorState } from "../components/ui/ErrorState";
import { Skeleton } from "../components/ui/Skeleton";
import { inspections, vehicles } from "../lib/api";
import { ApiError } from "../lib/api/client";
import type {
  Inspection,
  InspectionField,
  InspectionFieldType,
  InspectionTemplate,
  Vehicle,
} from "../lib/api/types";
import { useSession } from "../lib/session";

const fieldTypes: InspectionFieldType[] = [
  "text",
  "number",
  "date",
  "single",
  "multiple",
  "boolean",
  "photo",
  "note",
];

type FieldDraft = InspectionField & { optionsText: string; failureText: string };

function newField(index: number): FieldDraft {
  return {
    id: `field_${Date.now()}_${index}`,
    label: "",
    type: "boolean",
    required: false,
    options: [],
    failure_values: [false],
    create_plan_on_failure: false,
    optionsText: "",
    failureText: "false",
  };
}

function errorMessage(cause: unknown, fallback: string) {
  return cause instanceof ApiError ? cause.message : fallback;
}

function failedField(field: InspectionField, value: unknown) {
  const answers = Array.isArray(value) ? value : [value];
  return answers.some((answer) => field.failure_values.some((failure) => failure === answer));
}

export function Inspections() {
  const { t, i18n } = useTranslation();
  const { me } = useSession();
  const [vehicleList, setVehicleList] = useState<Vehicle[] | null>(null);
  const [templates, setTemplates] = useState<InspectionTemplate[] | null>(null);
  const [records, setRecords] = useState<Inspection[] | null>(null);
  const [vehicleId, setVehicleId] = useState("");
  const [templateForm, setTemplateForm] = useState<InspectionTemplate | "new" | null>(null);
  const [running, setRunning] = useState<Inspection | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const canWrite = me?.membership.role !== "reader";

  const loadBase = () => {
    setError(null);
    Promise.all([vehicles.list(), inspections.templates()])
      .then(([loadedVehicles, loadedTemplates]) => {
        setVehicleList(loadedVehicles);
        setTemplates(loadedTemplates);
        setVehicleId((current) => current || loadedVehicles[0]?.id || "");
      })
      .catch(setError);
  };

  const loadRecords = () => {
    if (!vehicleId) {
      setRecords([]);
      return;
    }
    inspections.list(vehicleId).then(setRecords).catch(setError);
  };

  useEffect(loadBase, []);
  useEffect(loadRecords, [vehicleId]);

  const selectedVehicle = vehicleList?.find((vehicle) => vehicle.id === vehicleId);
  const availableTemplates = useMemo(
    () => templates?.filter((template) => !template.vehicle_id || template.vehicle_id === vehicleId) ?? [],
    [templates, vehicleId],
  );

  async function start(template: InspectionTemplate) {
    if (!vehicleId) return;
    try {
      const item = await inspections.create(vehicleId, {
        template_id: template.id,
        recorded_on: new Date().toISOString().slice(0, 10),
      });
      setRunning(item);
      loadRecords();
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (cause) {
      setError(cause instanceof Error ? cause : new Error(t("common.error")));
    }
  }

  if (error) return <ErrorState onRetry={loadBase} />;
  if (!vehicleList || !templates || records === null) return <Skeleton lines={8} />;

  return (
    <div className="min-w-0 space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div className="min-w-0">
          <h1 className="text-2xl font-bold text-ink">{t("inspections.title")}</h1>
          <p className="mt-1 text-sm text-ink-subtle">{t("inspections.description")}</p>
        </div>
        {canWrite && (
          <button onClick={() => setTemplateForm("new")} className="self-start rounded-lg bg-copper px-4 py-2.5 text-sm font-semibold text-white">
            {t("inspections.newTemplate")}
          </button>
        )}
      </div>

      {vehicleList.length > 0 && (
        <label className="block max-w-md text-sm text-ink-muted">
          {t("nav.vehicle")}
          <select value={vehicleId} onChange={(event) => { setVehicleId(event.target.value); setRunning(null); }} className="mt-1 w-full rounded-lg border border-line px-3 py-2.5 bg-raised">
            {vehicleList.map((vehicle) => <option key={vehicle.id} value={vehicle.id}>{vehicle.name}</option>)}
          </select>
        </label>
      )}

      {templateForm && (
        <TemplateForm
          current={templateForm === "new" ? null : templateForm}
          vehicles={vehicleList}
          onCancel={() => setTemplateForm(null)}
          onSaved={() => { setTemplateForm(null); loadBase(); }}
        />
      )}

      {running && (
        <InspectionRunner
          inspection={running}
          unit={selectedVehicle?.distance_unit ?? "km"}
          onCancel={() => setRunning(null)}
          onSaved={(item) => { setRunning(item.status === "draft" ? item : null); loadRecords(); }}
        />
      )}

      <section className="space-y-3">
        <h2 className="text-lg font-semibold text-ink">{t("inspections.templates")}</h2>
        {availableTemplates.length === 0 ? (
          <p className="rounded-xl border border-dashed border-line-strong bg-raised p-7 text-center text-sm text-graphite/50">{t("inspections.emptyTemplates")}</p>
        ) : (
          <div className="grid min-w-0 gap-3 sm:grid-cols-2 xl:grid-cols-3">
            {availableTemplates.map((template) => (
              <article key={template.id} className="min-w-0 rounded-xl border border-line bg-raised p-4 shadow-sm">
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0"><h3 className="break-words font-semibold text-ink">{template.name}</h3><p className="text-xs text-ink-subtle">v{template.version} · {template.fields.length} {t("inspections.fields").toLocaleLowerCase(i18n.language)}</p></div>
                  {template.vehicle_id && <span className="shrink-0 rounded-full bg-copper/10 px-2 py-1 text-[10px] font-semibold text-copper">{selectedVehicle?.name}</span>}
                </div>
                <div className="mt-4 grid gap-2">
                  {canWrite && vehicleId && <button onClick={() => void start(template)} className="rounded-lg bg-copper px-3 py-2.5 text-sm font-semibold text-white">{t("inspections.start")}</button>}
                  {canWrite && <div className="grid grid-cols-2 gap-2"><button onClick={() => setTemplateForm(template)} className="rounded-lg border border-line px-2 py-2 text-sm font-semibold">{t("inspections.newVersion")}</button><button onClick={() => void inspections.duplicateTemplate(template.id).then(loadBase)} className="rounded-lg border border-line px-2 py-2 text-sm font-semibold">{t("inspections.duplicate")}</button></div>}
                </div>
              </article>
            ))}
          </div>
        )}
      </section>

      <section className="space-y-3">
        <h2 className="text-lg font-semibold text-ink">{t("inspections.history")}</h2>
        {records.length === 0 ? (
          <p className="rounded-xl border border-dashed border-line-strong bg-raised p-7 text-center text-sm text-graphite/50">{t("inspections.emptyHistory")}</p>
        ) : (
          <div className="space-y-3">
            {records.map((record) => <InspectionCard key={record.id} item={record} canWrite={Boolean(canWrite)} onContinue={() => setRunning(record)} />)}
          </div>
        )}
      </section>
    </div>
  );
}

function TemplateForm({ current, vehicles: vehicleList, onCancel, onSaved }: { current: InspectionTemplate | null; vehicles: Vehicle[]; onCancel: () => void; onSaved: () => void }) {
  const { t } = useTranslation();
  const [name, setName] = useState(current?.name ?? "");
  const [vehicleId, setVehicleId] = useState(current?.vehicle_id ?? "");
  const [fields, setFields] = useState<FieldDraft[]>(() => current?.fields.map((field) => ({ ...field, optionsText: field.options.join(", "), failureText: field.failure_values.join(", ") })) ?? [newField(0)]);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  function update(index: number, values: Partial<FieldDraft>) {
    setFields((items) => items.map((item, fieldIndex) => fieldIndex === index ? { ...item, ...values } : item));
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    setSaving(true); setError(null);
    const body = {
      name,
      vehicle_id: vehicleId || null,
      fields: fields.map(({ optionsText, failureText, ...field }) => ({
        ...field,
        options: optionsText.split(",").map((value) => value.trim()).filter(Boolean),
        failure_values: failureText.split(",").map((value) => value.trim()).filter(Boolean).map((value) => value === "true" ? true : value === "false" ? false : value),
      })),
    };
    try {
      if (current) await inspections.versionTemplate(current.id, body);
      else await inspections.createTemplate(body);
      onSaved();
    } catch (cause) {
      setError(errorMessage(cause, t("common.error")));
    } finally { setSaving(false); }
  }

  return (
    <form onSubmit={submit} className="space-y-4 rounded-xl border border-copper/25 bg-raised p-4 shadow-sm">
      <div className="grid gap-3 sm:grid-cols-2">
        <label className="text-sm">{t("inspections.templateName")}<input required value={name} onChange={(event) => setName(event.target.value)} className="mt-1 w-full rounded-lg border px-3 py-2.5 bg-raised" /></label>
        <label className="text-sm">{t("nav.vehicle")}<select value={vehicleId} onChange={(event) => setVehicleId(event.target.value)} className="mt-1 w-full rounded-lg border px-3 py-2.5 bg-raised"><option value="">{t("inspections.allVehicles")}</option>{vehicleList.map((vehicle) => <option key={vehicle.id} value={vehicle.id}>{vehicle.name}</option>)}</select></label>
      </div>
      <div className="space-y-3">
        <div className="flex items-center justify-between gap-3"><h3 className="font-semibold">{t("inspections.fields")}</h3><button type="button" onClick={() => setFields((items) => [...items, newField(items.length)])} className="flex items-center gap-1 rounded-lg border border-copper/30 px-3 py-2 text-sm font-semibold text-copper"><PlusIcon aria-hidden="true" className="h-4 w-4" />{t("inspections.addField")}</button></div>
        {fields.map((field, index) => (
          <fieldset key={field.id} className="grid min-w-0 gap-3 rounded-lg bg-graphite/[.03] p-3 dark:bg-white/[.04] sm:grid-cols-2">
            <label className="text-sm">{t("inspections.fieldLabel")}<input required value={field.label} onChange={(event) => update(index, { label: event.target.value })} className="mt-1 w-full rounded-lg border px-3 py-2.5 bg-raised" /></label>
            <label className="text-sm">{t("inspections.fieldType")}<select value={field.type} onChange={(event) => update(index, { type: event.target.value as InspectionFieldType })} className="mt-1 w-full rounded-lg border px-3 py-2.5 bg-raised">{fieldTypes.map((type) => <option key={type} value={type}>{t(`inspections.types.${type}`)}</option>)}</select></label>
            {(field.type === "single" || field.type === "multiple") && <label className="text-sm sm:col-span-2">{t("inspections.options")}<input required value={field.optionsText} onChange={(event) => update(index, { optionsText: event.target.value })} className="mt-1 w-full rounded-lg border px-3 py-2.5 bg-raised" /></label>}
            <label className="text-sm sm:col-span-2">{t("inspections.failureValues")}<input value={field.failureText} onChange={(event) => update(index, { failureText: event.target.value })} className="mt-1 w-full rounded-lg border px-3 py-2.5 bg-raised" /></label>
            <label className="flex min-h-11 items-center gap-2 text-sm"><input type="checkbox" checked={field.required} onChange={(event) => update(index, { required: event.target.checked })} />{t("inspections.required")}</label>
            <label className="flex min-h-11 items-center gap-2 text-sm"><input type="checkbox" checked={field.create_plan_on_failure} onChange={(event) => update(index, { create_plan_on_failure: event.target.checked })} />{t("inspections.createPlan")}</label>
            {fields.length > 1 && <button type="button" onClick={() => setFields((items) => items.filter((_, fieldIndex) => fieldIndex !== index))} className="flex items-center gap-1 justify-self-start text-sm font-semibold text-danger sm:col-span-2"><TrashIcon aria-hidden="true" className="h-4 w-4" />{t("inspections.removeField")}</button>}
          </fieldset>
        ))}
      </div>
      {error && <p role="alert" className="text-sm text-danger">{error}</p>}
      <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end"><button type="button" onClick={onCancel} className="rounded-lg border px-4 py-2.5">{t("common.cancel")}</button><button disabled={saving} className="rounded-lg bg-copper px-4 py-2.5 font-semibold text-white disabled:opacity-50">{t("inspections.saveTemplate")}</button></div>
    </form>
  );
}

function InspectionRunner({ inspection, unit, onCancel, onSaved }: { inspection: Inspection; unit: string; onCancel: () => void; onSaved: (item: Inspection) => void }) {
  const { t } = useTranslation();
  const [recordedOn, setRecordedOn] = useState(inspection.recorded_on);
  const [odometer, setOdometer] = useState(inspection.odometer?.toString() ?? "");
  const [notes, setNotes] = useState(inspection.notes ?? "");
  const [responses, setResponses] = useState<Record<string, unknown>>(inspection.responses);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  async function persist(complete: boolean) {
    setSaving(true); setError(null);
    try {
      const draft = await inspections.update(inspection.vehicle_id, inspection.id, {
        recorded_on: recordedOn,
        odometer: odometer ? Number(odometer) : null,
        responses,
        notes: notes || null,
      });
      const result = complete ? await inspections.complete(inspection.vehicle_id, draft.id) : draft;
      onSaved(result);
    } catch (cause) {
      setError(errorMessage(cause, t("common.error")));
    } finally { setSaving(false); }
  }

  return (
    <section className="space-y-4 rounded-xl border border-copper/25 bg-raised p-4 shadow-sm">
      <div><h2 className="break-words text-lg font-semibold">{inspection.template_snapshot.name}</h2><p className="text-xs text-ink-subtle">v{inspection.template_snapshot.version}</p></div>
      <div className="grid gap-3 sm:grid-cols-2">
        <label className="text-sm">{t("inspections.recordedOn")}<input required type="date" value={recordedOn} onChange={(event) => setRecordedOn(event.target.value)} className="mt-1 w-full rounded-lg border px-3 py-2.5 bg-raised" /></label>
        <label className="text-sm">{t("inspections.odometer")} ({unit})<input type="number" min="0" inputMode="numeric" value={odometer} onChange={(event) => setOdometer(event.target.value)} className="mt-1 w-full rounded-lg border px-3 py-2.5 bg-raised" /></label>
      </div>
      <div className="space-y-3">{inspection.template_snapshot.fields.map((field) => <ResponseField key={field.id} field={field} value={responses[field.id]} onChange={(value) => setResponses((current) => ({ ...current, [field.id]: value }))} />)}</div>
      <label className="block text-sm">{t("inspections.notes")}<textarea rows={3} value={notes} onChange={(event) => setNotes(event.target.value)} className="mt-1 w-full rounded-lg border px-3 py-2.5 bg-raised" /></label>
      {error && <p role="alert" className="text-sm text-danger">{error}</p>}
      <div className="grid gap-2 sm:flex sm:justify-end"><button type="button" onClick={onCancel} className="rounded-lg border px-4 py-2.5">{t("common.cancel")}</button><button disabled={saving} onClick={() => void persist(false)} className="rounded-lg border border-copper px-4 py-2.5 font-semibold text-copper disabled:opacity-50">{t("inspections.saveDraft")}</button><button disabled={saving} onClick={() => void persist(true)} className="rounded-lg bg-success-solid px-4 py-2.5 font-semibold text-white disabled:opacity-50">{t("inspections.complete")}</button></div>
    </section>
  );
}

function ResponseField({ field, value, onChange }: { field: InspectionField; value: unknown; onChange: (value: unknown) => void }) {
  const { t } = useTranslation();
  const classes = "mt-1 w-full rounded-lg border border-line px-3 py-2.5 bg-raised";
  const label = <span>{field.label}{field.required && <span className="ml-1 text-danger">*</span>}</span>;
  if (field.type === "boolean") return <label className="block text-sm">{label}<select value={typeof value === "boolean" ? String(value) : ""} onChange={(event) => onChange(event.target.value === "" ? undefined : event.target.value === "true")} className={classes}><option value="">—</option><option value="true">{t("inspections.yes")}</option><option value="false">{t("inspections.no")}</option></select></label>;
  if (field.type === "single") return <label className="block text-sm">{label}<select value={typeof value === "string" ? value : ""} onChange={(event) => onChange(event.target.value)} className={classes}><option value="">—</option>{field.options.map((option) => <option key={option}>{option}</option>)}</select></label>;
  if (field.type === "multiple") { const selected = Array.isArray(value) ? value : []; return <fieldset className="rounded-lg border border-line p-3"><legend className="px-1 text-sm">{label}</legend><div className="grid gap-2 sm:grid-cols-2">{field.options.map((option) => <label key={option} className="flex min-h-11 items-center gap-2 text-sm"><input type="checkbox" checked={selected.includes(option)} onChange={(event) => onChange(event.target.checked ? [...selected, option] : selected.filter((entry) => entry !== option))} />{option}</label>)}</div></fieldset>; }
  if (field.type === "photo") return <label className="block text-sm">{label}<span className="mt-1 block rounded-lg border border-dashed p-3"><input type="file" accept="image/*" capture="environment" onChange={(event) => { const file = event.target.files?.[0]; if (!file) return; const reader = new FileReader(); reader.onload = () => onChange(reader.result); reader.readAsDataURL(file); }} />{typeof value === "string" && value.startsWith("data:image/") && <img src={value} alt="" className="mt-3 max-h-48 w-full rounded-lg object-contain" />}</span></label>;
  if (field.type === "note") return <label className="block text-sm">{label}<textarea rows={3} value={typeof value === "string" ? value : ""} onChange={(event) => onChange(event.target.value)} className={classes} /></label>;
  return <label className="block text-sm">{label}<input type={field.type} value={typeof value === "string" || typeof value === "number" ? value : ""} onChange={(event) => onChange(field.type === "number" && event.target.value ? Number(event.target.value) : event.target.value)} className={classes} /></label>;
}

function InspectionCard({ item, canWrite, onContinue }: { item: Inspection; canWrite: boolean; onContinue: () => void }) {
  const { t, i18n } = useTranslation();
  const result = item.status === "draft" ? "draft" : item.result ?? "draft";
  const statusClass = result === "failed" ? "bg-danger-soft text-danger" : result === "draft" ? "bg-warning-soft text-warning" : "bg-success-soft text-success";
  return <article className="min-w-0 rounded-xl border border-line bg-raised p-4 shadow-sm"><div className="flex min-w-0 flex-col gap-2 sm:flex-row sm:items-start sm:justify-between"><div className="min-w-0"><h3 className="break-words font-semibold">{item.template_snapshot.name}</h3><p className="text-xs text-ink-subtle">{new Intl.DateTimeFormat(i18n.language).format(new Date(`${item.recorded_on}T12:00:00`))} · v{item.template_snapshot.version}{item.odometer !== null ? ` · ${item.odometer.toLocaleString(i18n.language)} km` : ""}</p></div><span className={`self-start rounded-full px-2 py-1 text-[10px] font-bold uppercase ${statusClass}`}>{t(`inspections.${result}`)}</span></div>{item.status === "completed" && <div className="mt-3 space-y-1">{item.template_snapshot.fields.filter((field) => failedField(field, item.responses[field.id])).map((field) => <p key={field.id} className="flex items-center gap-1.5 rounded-md bg-danger-soft px-3 py-2 text-sm font-medium text-danger"><XMarkIcon aria-hidden="true" className="h-4 w-4 shrink-0" />{field.label}</p>)}</div>}{item.notes && <p className="mt-3 whitespace-pre-wrap break-words text-sm text-ink-muted">{item.notes}</p>}{item.status === "draft" && canWrite && <button onClick={onContinue} className="mt-4 w-full rounded-lg bg-copper px-3 py-2.5 text-sm font-semibold text-white sm:w-auto">{t("inspections.continue")}</button>}</article>;
}
