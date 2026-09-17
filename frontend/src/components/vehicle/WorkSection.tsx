import { useState } from "react";
import type { FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { TrashIcon } from "@heroicons/react/24/outline";

import { workRecords } from "../../lib/api";
import { ApiError } from "../../lib/api/client";
import type { WorkKind, WorkRecord, WorkRecordItemInput } from "../../lib/api/types";
import { useConfirm } from "../../components/ui/confirm-context";

const CONTROL = "rounded-md border border-line bg-raised px-3 py-2";

function blankItem(): WorkRecordItemInput {
  return { description: "", quantity: "1" };
}
export function WorkSection({
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
  const confirm = useConfirm();
  const [show, setShow] = useState(false);
  const [description, setDescription] = useState("");
  const [cost, setCost] = useState("");
  const [labour, setLabour] = useState("");
  const [parts, setParts] = useState("");
  const [tax, setTax] = useState("");
  const [discount, setDiscount] = useState("");
  const [items, setItems] = useState<WorkRecordItemInput[]>([]);
  const [kind, setKind] = useState<WorkKind>("maintenance");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  async function submit(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const decimal = (value: string) => value.replace(",", ".") || undefined;
      await workRecords.create(vehicleId, {
        recorded_on: new Date().toISOString().slice(0, 10),
        kind,
        description,
        total_cost: decimal(cost),
        labour_cost: decimal(labour),
        parts_cost: decimal(parts),
        tax_cost: decimal(tax),
        discount: decimal(discount),
        odometer_reading: currentReading ?? undefined,
        // Blank rows are the ones the member added and never filled in.
        items: items
          .filter((item) => item.description.trim())
          .map((item) => ({
            description: item.description.trim(),
            quantity: item.quantity.replace(",", ".") || "1",
            unit_cost: item.unit_cost ? item.unit_cost.replace(",", ".") : undefined,
          })),
      });
      setShow(false);
      setDescription("");
      setCost("");
      setLabour("");
      setParts("");
      setTax("");
      setDiscount("");
      setItems([]);
      onCreated();
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : t("common.error"));
    } finally {
      setSaving(false);
    }
  }
  async function remove(id: string) {
    if (await confirm(t("common.confirmDelete"))) {
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
          <p className="text-sm text-ink-subtle">{t("work.description")}</p>
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
            className={CONTROL}
          />

          <fieldset className="rounded-lg border border-line p-3 sm:col-span-2">
            <legend className="px-1 text-sm font-medium">{t("work.breakdown")}</legend>
            <p className="mb-2 text-xs text-ink-subtle">{t("work.breakdownHint")}</p>
            <div className="grid gap-2 sm:grid-cols-4">
              <input
                inputMode="decimal"
                placeholder={t("work.labour")}
                value={labour}
                onChange={(event) => setLabour(event.target.value)}
                className={CONTROL}
              />
              <input
                inputMode="decimal"
                placeholder={t("work.parts")}
                value={parts}
                onChange={(event) => setParts(event.target.value)}
                className={CONTROL}
              />
              <input
                inputMode="decimal"
                placeholder={t("work.tax")}
                value={tax}
                onChange={(event) => setTax(event.target.value)}
                className={CONTROL}
              />
              <input
                inputMode="decimal"
                placeholder={t("work.discount")}
                value={discount}
                onChange={(event) => setDiscount(event.target.value)}
                className={CONTROL}
              />
            </div>
          </fieldset>

          <fieldset className="rounded-lg border border-line p-3 sm:col-span-2">
            <legend className="px-1 text-sm font-medium">{t("work.items")}</legend>
            {items.map((item, index) => (
              <div key={index} className="mb-2 grid gap-2 sm:grid-cols-[2fr_1fr_1fr_auto]">
                <input
                  aria-label={t("work.itemDescription")}
                  placeholder={t("work.itemDescription")}
                  value={item.description}
                  onChange={(event) =>
                    setItems(
                      items.map((one, at) =>
                        at === index ? { ...one, description: event.target.value } : one,
                      ),
                    )
                  }
                  className={CONTROL}
                />
                <input
                  aria-label={t("work.itemQuantity")}
                  inputMode="decimal"
                  placeholder={t("work.itemQuantity")}
                  value={item.quantity}
                  onChange={(event) =>
                    setItems(
                      items.map((one, at) =>
                        at === index ? { ...one, quantity: event.target.value } : one,
                      ),
                    )
                  }
                  className={CONTROL}
                />
                <input
                  aria-label={t("work.itemUnitCost")}
                  inputMode="decimal"
                  placeholder={t("work.itemUnitCost")}
                  value={item.unit_cost ?? ""}
                  onChange={(event) =>
                    setItems(
                      items.map((one, at) =>
                        at === index ? { ...one, unit_cost: event.target.value } : one,
                      ),
                    )
                  }
                  className={CONTROL}
                />
                <button
                  type="button"
                  aria-label={`${t("common.delete")} ${index + 1}`}
                  onClick={() => setItems(items.filter((_, at) => at !== index))}
                  className="rounded-md border border-line px-2 text-danger"
                >
                  <TrashIcon aria-hidden="true" className="h-4 w-4" />
                </button>
              </div>
            ))}
            <button
              type="button"
              onClick={() => setItems([...items, blankItem()])}
              className="rounded-md border border-dashed border-line px-3 py-1.5 text-sm text-ink-muted"
            >
              {t("work.addItem")}
            </button>
          </fieldset>

          {error && <p className="text-sm text-danger sm:col-span-2">{error}</p>}
          <button
            disabled={saving}
            className="rounded-md bg-copper px-4 py-2 text-sm font-medium text-white disabled:opacity-60"
          >
            {t("garage.save")}
          </button>
        </form>
      )}
      <ul className="divide-y divide-line">
        {records.map((record) => (
          <li
            key={record.id}
            className="flex min-w-0 flex-col gap-2 py-3 sm:flex-row sm:justify-between sm:gap-4"
          >
            <div className="min-w-0">
              <p className="break-words font-medium text-ink">
                {record.description}
              </p>
              <p className="text-sm text-ink-subtle">
                {t(`work.${record.kind}`)}
                {record.supplier ? ` · ${record.supplier}` : ""}
              </p>
              {record.items.length > 0 && (
                <ul className="mt-1 text-xs text-ink-subtle">
                  {record.items.map((item) => (
                    <li key={item.id}>
                      {Number(item.quantity)} × {item.description}
                      {item.unit_cost
                        ? ` · ${Number(item.unit_cost).toLocaleString(i18n.language, {
                            style: "currency",
                            currency: "EUR",
                          })}`
                        : ""}
                    </li>
                  ))}
                </ul>
              )}
            </div>
            <div className="flex shrink-0 items-center gap-3">
              <p className="text-sm text-ink-subtle">
                {record.total_cost
                  ? Number(record.total_cost).toLocaleString(i18n.language, {
                      style: "currency",
                      currency: "EUR",
                    })
                  : "—"}
              </p>
              <button
                onClick={() => void remove(record.id)}
                className="flex items-center gap-1 text-xs font-medium text-danger"
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
