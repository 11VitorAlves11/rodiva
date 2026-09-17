import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { customFields } from "../../lib/api";
import type { CustomField, CustomFieldType } from "../../lib/api/types";
import { Button } from "../ui/Button";
import { Field, Input, Select } from "../ui/Field";
import { useConfirm } from "../ui/confirm-context";

const KINDS = ["vehicle", "fuel", "work", "expense", "note", "plan", "inspection"];
const TYPES: CustomFieldType[] = [
  "text",
  "number",
  "currency",
  "date",
  "choice",
  "multi_choice",
  "checkbox",
  "url",
  "secret",
];

/** A key is the stable identifier, so it is derived once and never edited. */
function keyFrom(label: string): string {
  return label
    .normalize("NFKD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "")
    .slice(0, 50);
}

export function CustomFieldSettings({ canManage }: { canManage: boolean }) {
  const { t } = useTranslation();
  const confirm = useConfirm();
  const [fields, setFields] = useState<CustomField[] | null>(null);
  const [kind, setKind] = useState("vehicle");
  const [label, setLabel] = useState("");
  const [fieldType, setFieldType] = useState<CustomFieldType>("text");
  const [options, setOptions] = useState("");
  const [required, setRequired] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const reload = () =>
    customFields
      .list()
      .then(setFields)
      .catch(() => setFields([]));

  useEffect(() => {
    void reload();
  }, []);

  const needsOptions = fieldType === "choice" || fieldType === "multi_choice";

  async function create() {
    const key = keyFrom(label);
    if (!key) {
      setError(t("customFields.labelNeeded"));
      return;
    }
    setError(null);
    try {
      await customFields.create({
        record_kind: kind,
        key,
        label: label.trim(),
        field_type: fieldType,
        required,
        options: needsOptions
          ? options
              .split(",")
              .map((one) => one.trim())
              .filter(Boolean)
          : [],
      });
      setLabel("");
      setOptions("");
      setRequired(false);
      await reload();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : t("common.error"));
    }
  }

  async function archive(field: CustomField) {
    if (!(await confirm(t("customFields.confirmArchive", { label: field.label })))) return;
    await customFields.update(field.id, { archived: true });
    await reload();
  }

  return (
    <section className="rounded-xl border border-line bg-raised p-5 shadow-sm">
      <h2 className="mb-1 font-semibold text-ink">{t("customFields.title")}</h2>
      <p className="mb-4 text-sm text-ink-muted">{t("customFields.description")}</p>

      {canManage && (
        <div className="mb-4 grid gap-3 sm:grid-cols-2">
          <Field label={t("customFields.recordKind")}>
            <Select value={kind} onChange={(event) => setKind(event.target.value)}>
              {KINDS.map((one) => (
                <option key={one} value={one}>
                  {t(`customFields.kinds.${one}`)}
                </option>
              ))}
            </Select>
          </Field>
          <Field label={t("customFields.label")} hint={label ? keyFrom(label) : undefined}>
            <Input value={label} maxLength={100} onChange={(e) => setLabel(e.target.value)} />
          </Field>
          <Field label={t("customFields.type")}>
            <Select
              value={fieldType}
              onChange={(event) => setFieldType(event.target.value as CustomFieldType)}
            >
              {TYPES.map((one) => (
                <option key={one} value={one}>
                  {t(`customFields.types.${one}`)}
                </option>
              ))}
            </Select>
          </Field>
          {needsOptions && (
            <Field label={t("customFields.options")} hint={t("customFields.optionsHint")}>
              <Input value={options} onChange={(event) => setOptions(event.target.value)} />
            </Field>
          )}
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={required}
              onChange={(event) => setRequired(event.target.checked)}
            />
            {t("customFields.required")}
          </label>
          <div className="flex items-end">
            <Button onClick={() => void create()} disabled={!label.trim()}>
              {t("customFields.create")}
            </Button>
          </div>
        </div>
      )}

      {error && <p className="mb-3 text-sm text-danger">{error}</p>}
      {fields === null && <p className="text-sm text-ink-muted">{t("common.loading")}</p>}
      {fields?.length === 0 && <p className="text-sm text-ink-muted">{t("customFields.noneYet")}</p>}

      <ul className="divide-y divide-line">
        {fields?.map((field) => (
          <li key={field.id} className="flex flex-wrap items-center gap-3 py-2.5 text-sm">
            <span className="font-medium text-ink">{field.label}</span>
            <span className="text-xs text-ink-muted">
              {t(`customFields.kinds.${field.record_kind}`, { defaultValue: field.record_kind })} ·{" "}
              {t(`customFields.types.${field.field_type}`)}
              {field.required ? ` · ${t("customFields.required")}` : ""}
            </span>
            {canManage && (
              <Button
                variant="danger"
                size="sm"
                className="ml-auto"
                onClick={() => void archive(field)}
              >
                {t("customFields.archive")}
              </Button>
            )}
          </li>
        ))}
      </ul>
    </section>
  );
}
