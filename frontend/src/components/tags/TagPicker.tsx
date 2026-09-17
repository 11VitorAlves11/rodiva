import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { tags as tagsApi } from "../../lib/api";
import type { Tag, TaggableKind, TagUsage } from "../../lib/api/types";
import { cn } from "../../lib/cn";
import { TagChip } from "../ui/TagChip";

/**
 * Picks which of the household's tags sit on one record.
 *
 * The full set is sent on every change rather than a delta, matching the API:
 * what the member sees selected is what the record ends up with.
 */
export function TagPicker({
  kind,
  recordId,
  canEdit,
  className,
}: {
  kind: TaggableKind;
  recordId: string;
  canEdit: boolean;
  className?: string;
}) {
  const { t } = useTranslation();
  const [available, setAvailable] = useState<TagUsage[] | null>(null);
  const [selected, setSelected] = useState<Tag[]>([]);
  const [open, setOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const [all, mine] = await Promise.all([
          tagsApi.list(),
          tagsApi.forRecord(kind, recordId),
        ]);
        if (cancelled) return;
        setAvailable(all);
        setSelected(mine);
      } catch {
        if (!cancelled) setAvailable([]);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [kind, recordId]);

  async function apply(next: Tag[]) {
    const previous = selected;
    setSelected(next);
    setError(null);
    try {
      const saved = await tagsApi.setForRecord(
        kind,
        recordId,
        next.map((tag) => tag.id),
      );
      setSelected(saved);
    } catch {
      setSelected(previous);
      setError(t("tags.saveFailed"));
    }
  }

  const selectedIds = new Set(selected.map((tag) => tag.id));

  return (
    <div className={cn("flex flex-wrap items-center gap-1.5", className)}>
      {selected.map((tag) => (
        <TagChip
          key={tag.id}
          tag={tag}
          removeLabel={t("tags.remove", { name: tag.name })}
          onRemove={
            canEdit ? () => void apply(selected.filter((item) => item.id !== tag.id)) : undefined
          }
        />
      ))}

      {canEdit && (
        <div className="relative">
          <button
            type="button"
            onClick={() => setOpen((value) => !value)}
            aria-expanded={open}
            className="rounded-full border border-dashed border-line px-2 py-0.5 text-xs font-semibold text-ink-muted transition-colors hover:border-brand hover:text-brand"
          >
            {t("tags.add")}
          </button>
          {open && (
            <div className="absolute z-10 mt-1 max-h-56 w-56 overflow-y-auto rounded-lg border border-line bg-raised p-1 shadow-lg">
              {available === null && (
                <p className="px-2 py-1.5 text-xs text-ink-muted">{t("common.loading")}</p>
              )}
              {available?.length === 0 && (
                <p className="px-2 py-1.5 text-xs text-ink-muted">{t("tags.noneYet")}</p>
              )}
              {available?.map((tag) => {
                const isOn = selectedIds.has(tag.id);
                return (
                  <button
                    key={tag.id}
                    type="button"
                    onClick={() =>
                      void apply(
                        isOn
                          ? selected.filter((item) => item.id !== tag.id)
                          : [...selected, tag],
                      )
                    }
                    className="flex w-full items-center gap-2 rounded px-2 py-1.5 text-left text-sm text-ink hover:bg-sunken"
                  >
                    <span
                      aria-hidden="true"
                      className="size-2.5 shrink-0 rounded-full ring-1 ring-inset ring-black/10"
                      style={{ backgroundColor: tag.color }}
                    />
                    <span className="flex-1 truncate">{tag.name}</span>
                    <span className="text-xs text-ink-muted">{isOn ? "✓" : ""}</span>
                  </button>
                );
              })}
            </div>
          )}
        </div>
      )}

      {error && <span className="text-xs text-danger">{error}</span>}
    </div>
  );
}
