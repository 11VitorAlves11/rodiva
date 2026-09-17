import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { tags as tagsApi } from "../../lib/api";
import type { TagUsage } from "../../lib/api/types";
import { Button } from "../ui/Button";
import { Field, Input } from "../ui/Field";
import { useConfirm } from "../../components/ui/confirm-context";

/** A short, legible set to pick from, rather than a full colour wheel. */
const PALETTE = [
  "#B94A22",
  "#A8611B",
  "#7A6A1F",
  "#2F6F4E",
  "#1F6F76",
  "#2B5FA8",
  "#5B4B96",
  "#8C3F63",
  "#6B7280",
];

export function TagSettings({ canManage }: { canManage: boolean }) {
  const { t } = useTranslation();
  const confirm = useConfirm();
  const [items, setItems] = useState<TagUsage[] | null>(null);
  const [name, setName] = useState("");
  const [color, setColor] = useState(PALETTE[0]);
  const [error, setError] = useState<string | null>(null);

  async function reload() {
    setItems(await tagsApi.list());
  }

  useEffect(() => {
    void reload().catch(() => setItems([]));
  }, []);

  async function create() {
    if (!name.trim()) return;
    setError(null);
    try {
      await tagsApi.create({ name: name.trim(), color });
      setName("");
      await reload();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : t("tags.saveFailed"));
    }
  }

  async function remove(tag: TagUsage) {
    if (!await confirm(t("tags.confirmDelete", { name: tag.name, count: tag.record_count })))
      return;
    setError(null);
    try {
      await tagsApi.remove(tag.id);
      await reload();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : t("tags.saveFailed"));
    }
  }

  async function recolour(tag: TagUsage, next: string) {
    setError(null);
    try {
      await tagsApi.update(tag.id, { color: next });
      await reload();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : t("tags.saveFailed"));
    }
  }

  return (
    <section className="rounded-xl border border-line bg-raised p-5 shadow-sm">
      <h2 className="mb-1 font-semibold text-ink">{t("tags.title")}</h2>
      <p className="mb-4 text-sm text-ink-muted">{t("tags.description")}</p>

      {canManage && (
        <div className="mb-4 flex flex-wrap items-end gap-3">
          <Field label={t("tags.name")} className="min-w-48 flex-1">
            <Input
              value={name}
              maxLength={50}
              onChange={(event) => setName(event.target.value)}
              placeholder={t("tags.namePlaceholder")}
            />
          </Field>
          <div>
            <span className="mb-1 block text-sm font-medium text-ink-muted">
              {t("tags.colour")}
            </span>
            <div className="flex flex-wrap gap-1.5">
              {PALETTE.map((option) => (
                <button
                  key={option}
                  type="button"
                  aria-label={option}
                  aria-pressed={color === option}
                  onClick={() => setColor(option)}
                  className={`size-6 rounded-full ring-2 ring-offset-2 ring-offset-raised transition-all ${
                    color === option ? "ring-brand" : "ring-transparent"
                  }`}
                  style={{ backgroundColor: option }}
                />
              ))}
            </div>
          </div>
          <Button onClick={() => void create()} disabled={!name.trim()}>
            {t("tags.create")}
          </Button>
        </div>
      )}

      {error && <p className="mb-3 text-sm text-danger">{error}</p>}

      {items === null && <p className="text-sm text-ink-muted">{t("common.loading")}</p>}
      {items?.length === 0 && <p className="text-sm text-ink-muted">{t("tags.noneYet")}</p>}

      <ul className="divide-y divide-line">
        {items?.map((tag) => (
          <li key={tag.id} className="flex flex-wrap items-center gap-3 py-2.5">
            <span
              aria-hidden="true"
              className="size-3 shrink-0 rounded-full ring-1 ring-inset ring-black/10"
              style={{ backgroundColor: tag.color }}
            />
            <span className="font-medium text-ink">{tag.name}</span>
            <span className="text-xs text-ink-muted">
              {t("tags.usage", { count: tag.record_count })}
            </span>
            {canManage && (
              <div className="ml-auto flex items-center gap-1.5">
                {PALETTE.map((option) => (
                  <button
                    key={option}
                    type="button"
                    aria-label={`${tag.name} ${option}`}
                    onClick={() => void recolour(tag, option)}
                    className={`size-4 rounded-full transition-transform hover:scale-125 ${
                      tag.color.toLowerCase() === option.toLowerCase()
                        ? "ring-2 ring-brand ring-offset-1 ring-offset-raised"
                        : ""
                    }`}
                    style={{ backgroundColor: option }}
                  />
                ))}
                <Button variant="danger" size="sm" onClick={() => void remove(tag)}>
                  {t("settings.remove")}
                </Button>
              </div>
            )}
          </li>
        ))}
      </ul>
    </section>
  );
}
