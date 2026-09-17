import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { XMarkIcon } from "@heroicons/react/20/solid";

import { Skeleton } from "../components/ui/Skeleton";
import { NAV_ICONS } from "../lib/icons";
import { search, tags as tagsApi, vehicles } from "../lib/api";
import { ApiError } from "../lib/api/client";
import type {
  BulkFailure,
  BulkItem,
  SavedView,
  SearchKind,
  SearchResult,
  SearchSort,
  TagUsage,
  Vehicle,
} from "../lib/api/types";
import { TagChip } from "../components/ui/TagChip";

const KINDS: SearchKind[] = [
  "vehicle",
  "fuel",
  "work",
  "expense",
  "note",
  "plan",
  "inventory",
  "equipment",
  "inspection",
];

const SORTS: SearchSort[] = ["occurred_on_desc", "occurred_on_asc", "title_asc", "title_desc"];

export function Search() {
  const { t, i18n } = useTranslation();

  const [term, setTerm] = useState("");
  const [appliedTerm, setAppliedTerm] = useState("");
  const [kinds, setKinds] = useState<SearchKind[]>([]);
  const [vehicleIds, setVehicleIds] = useState<string[]>([]);
  const [tagIds, setTagIds] = useState<string[]>([]);
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [sort, setSort] = useState<SearchSort>("occurred_on_desc");

  const [vehicleList, setVehicleList] = useState<Vehicle[] | null>(null);
  const [tagList, setTagList] = useState<TagUsage[] | null>(null);
  const [savedViews, setSavedViews] = useState<SavedView[] | null>(null);
  const [results, setResults] = useState<SearchResult[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [moveTarget, setMoveTarget] = useState("");
  const [failures, setFailures] = useState<BulkFailure[]>([]);
  const [busy, setBusy] = useState(false);

  const reloadSavedViews = () => {
    search.savedViews.list().then(setSavedViews).catch(() => setSavedViews([]));
  };

  useEffect(() => {
    vehicles.list().then(setVehicleList).catch(() => setVehicleList([]));
    tagsApi.list().then(setTagList).catch(() => setTagList([]));
    reloadSavedViews();
  }, []);

  const runSearch = () => {
    setError(null);
    setResults(null);
    setFailures([]);
    setSelected(new Set());
    search
      .query({
        q: appliedTerm.trim() || undefined,
        kind: kinds.length ? kinds : undefined,
        vehicle_id: vehicleIds.length ? vehicleIds : undefined,
        tag_id: tagIds.length ? tagIds : undefined,
        date_from: dateFrom || undefined,
        date_to: dateTo || undefined,
        sort,
      })
      .then(setResults)
      .catch((cause) => setError(cause instanceof ApiError ? cause.message : t("common.error")));
  };

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(runSearch, [appliedTerm, kinds, vehicleIds, dateFrom, dateTo, sort]);

  function submit(event: FormEvent) {
    event.preventDefault();
    setAppliedTerm(term);
  }

  function toggleKind(value: SearchKind) {
    setKinds((current) =>
      current.includes(value) ? current.filter((item) => item !== value) : [...current, value],
    );
  }

  function toggleVehicle(id: string) {
    setVehicleIds((current) =>
      current.includes(id) ? current.filter((item) => item !== id) : [...current, id],
    );
  }

  function toggleTag(id: string) {
    setTagIds((current) =>
      current.includes(id) ? current.filter((item) => item !== id) : [...current, id],
    );
  }

  function toggleSelected(key: string) {
    setSelected((current) => {
      const next = new Set(current);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }

  async function saveCurrentView() {
    const name = window.prompt(t("search.savedViewNamePrompt"));
    if (!name || !name.trim()) return;
    try {
      await search.savedViews.create({
        name: name.trim(),
        query: {
          q: appliedTerm || undefined,
          kind: kinds,
          vehicle_id: vehicleIds,
          tag_id: tagIds,
          date_from: dateFrom || undefined,
          date_to: dateTo || undefined,
          sort,
        },
      });
      reloadSavedViews();
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : t("common.error"));
    }
  }

  function applySavedView(view: SavedView) {
    const query = view.query as {
      q?: string;
      kind?: SearchKind[];
      vehicle_id?: string[];
      tag_id?: string[];
      date_from?: string;
      date_to?: string;
      sort?: SearchSort;
    };
    setTerm(query.q ?? "");
    setAppliedTerm(query.q ?? "");
    setKinds(query.kind ?? []);
    setVehicleIds(query.vehicle_id ?? []);
    setTagIds(query.tag_id ?? []);
    setDateFrom(query.date_from ?? "");
    setDateTo(query.date_to ?? "");
    setSort(query.sort ?? "occurred_on_desc");
  }

  async function deleteSavedView(id: string) {
    if (!window.confirm(t("common.confirmDelete"))) return;
    try {
      await search.savedViews.remove(id);
      reloadSavedViews();
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : t("common.error"));
    }
  }

  function selectedItems(): BulkItem[] {
    if (!results) return [];
    return results
      .filter((item) => selected.has(`${item.kind}-${item.id}`))
      .map((item) => ({ kind: item.kind, id: item.id }));
  }

  async function runBulk(
    operation: "delete" | "duplicate" | "move",
    targetVehicleId?: string,
  ) {
    const items = selectedItems();
    if (items.length === 0) return;
    setBusy(true);
    setFailures([]);
    try {
      const result = await search.bulk({ operation, items, target_vehicle_id: targetVehicleId });
      setFailures(result.failures);
      runSearch();
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : t("common.error"));
    } finally {
      setBusy(false);
    }
  }

  async function exportSelected() {
    const items = selectedItems();
    if (items.length === 0) return;
    setBusy(true);
    try {
      const blob = await search.exportCsv(items);
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "rodiva-search-export.csv";
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : t("common.error"));
    } finally {
      setBusy(false);
    }
  }

  function confirmDelete() {
    const count = selected.size;
    if (window.confirm(t("search.bulkDeleteConfirm", { count }))) void runBulk("delete");
  }

  function confirmMove() {
    const count = selected.size;
    const vehicleName = vehicleList?.find((item) => item.id === moveTarget)?.name ?? "";
    if (!moveTarget) return;
    if (window.confirm(t("search.bulkMoveConfirm", { count, vehicle: vehicleName }))) {
      void runBulk("move", moveTarget);
    }
  }

  const activeFilters: Array<{ key: string; label: string; onRemove: () => void }> = [];
  if (appliedTerm) {
    activeFilters.push({
      key: "q",
      label: `"${appliedTerm}"`,
      onRemove: () => {
        setTerm("");
        setAppliedTerm("");
      },
    });
  }
  for (const value of kinds) {
    activeFilters.push({
      key: `kind-${value}`,
      label: t(`search.kinds.${value}`),
      onRemove: () => toggleKind(value),
    });
  }
  for (const id of vehicleIds) {
    const name = vehicleList?.find((item) => item.id === id)?.name ?? id;
    activeFilters.push({ key: `vehicle-${id}`, label: name, onRemove: () => toggleVehicle(id) });
  }
  for (const id of tagIds) {
    const name = tagList?.find((item) => item.id === id)?.name ?? id;
    activeFilters.push({ key: `tag-${id}`, label: name, onRemove: () => toggleTag(id) });
  }
  if (dateFrom) {
    activeFilters.push({
      key: "date_from",
      label: `${t("reports.from")}: ${dateFrom}`,
      onRemove: () => setDateFrom(""),
    });
  }
  if (dateTo) {
    activeFilters.push({
      key: "date_to",
      label: `${t("reports.to")}: ${dateTo}`,
      onRemove: () => setDateTo(""),
    });
  }

  return (
    <div className="min-w-0 space-y-5">
      <div>
        <h1 className="text-2xl font-bold text-ink">{t("search.title")}</h1>
        <p className="mt-1 text-sm text-ink-subtle">
          {t("search.description")}
        </p>
      </div>

      <form onSubmit={submit} className="flex min-w-0 flex-col gap-2 sm:flex-row">
        <input
          autoFocus
          type="search"
          value={term}
          onChange={(event) => setTerm(event.target.value)}
          placeholder={t("search.placeholder")}
          className="min-w-0 flex-1 rounded-lg border border-line px-3 py-3 bg-raised"
        />
        <button className="rounded-lg bg-copper px-5 py-3 font-semibold text-white">
          {t("search.submit")}
        </button>
      </form>

      <section className="space-y-3 rounded-xl border border-line bg-raised p-4">
        <fieldset>
          <legend className="mb-2 text-sm font-medium">{t("search.kindFilter")}</legend>
          <div className="flex flex-wrap gap-2">
            {KINDS.map((value) => (
              <label
                key={value}
                className="flex items-center gap-1.5 rounded-full border border-line px-3 py-1.5 text-sm"
              >
                <input
                  type="checkbox"
                  checked={kinds.includes(value)}
                  onChange={() => toggleKind(value)}
                />
                {t(`search.kinds.${value}`)}
              </label>
            ))}
          </div>
        </fieldset>

        {vehicleList && vehicleList.length > 0 && (
          <fieldset>
            <legend className="mb-2 text-sm font-medium">{t("search.vehicleFilter")}</legend>
            <div className="flex flex-wrap gap-2">
              {vehicleList.map((vehicle) => (
                <label
                  key={vehicle.id}
                  className="flex items-center gap-1.5 rounded-full border border-line px-3 py-1.5 text-sm"
                >
                  <input
                    type="checkbox"
                    checked={vehicleIds.includes(vehicle.id)}
                    onChange={() => toggleVehicle(vehicle.id)}
                  />
                  {vehicle.name}
                </label>
              ))}
            </div>
          </fieldset>
        )}

        {tagList && tagList.length > 0 && (
          <fieldset>
            <legend className="mb-2 text-sm font-medium">{t("tags.filter")}</legend>
            <div className="flex flex-wrap gap-2">
              {tagList.map((tag) => (
                <label
                  key={tag.id}
                  className="flex items-center gap-1.5 rounded-full border border-line px-3 py-1.5 text-sm"
                >
                  <input
                    type="checkbox"
                    checked={tagIds.includes(tag.id)}
                    onChange={() => toggleTag(tag.id)}
                  />
                  <span
                    aria-hidden="true"
                    className="size-2.5 shrink-0 rounded-full ring-1 ring-inset ring-black/10"
                    style={{ backgroundColor: tag.color }}
                  />
                  {tag.name}
                </label>
              ))}
            </div>
          </fieldset>
        )}

        <div className="grid gap-3 sm:grid-cols-3">
          <label className="text-sm">
            {t("reports.from")}
            <input
              type="date"
              value={dateFrom}
              onChange={(event) => setDateFrom(event.target.value)}
              className="mt-1 w-full rounded-lg border border-line px-3 py-2.5 bg-raised"
            />
          </label>
          <label className="text-sm">
            {t("reports.to")}
            <input
              type="date"
              value={dateTo}
              onChange={(event) => setDateTo(event.target.value)}
              className="mt-1 w-full rounded-lg border border-line px-3 py-2.5 bg-raised"
            />
          </label>
          <label className="text-sm">
            {t("search.sort")}
            <select
              value={sort}
              onChange={(event) => setSort(event.target.value as SearchSort)}
              className="mt-1 w-full rounded-lg border border-line px-3 py-2.5 bg-raised"
            >
              {SORTS.map((value) => (
                <option key={value} value={value}>
                  {t(`search.sorts.${value}`)}
                </option>
              ))}
            </select>
          </label>
        </div>

        <button
          type="button"
          onClick={saveCurrentView}
          className="rounded-lg border border-line px-4 py-2.5 text-sm font-semibold"
        >
          {t("search.saveView")}
        </button>

        {savedViews && savedViews.length > 0 && (
          <div className="flex flex-wrap items-center gap-2 border-t border-line pt-3">
            <span className="text-sm font-medium">{t("search.savedViewsLabel")}</span>
            {savedViews.map((view) => (
              <span
                key={view.id}
                className="flex items-center gap-1 rounded-full bg-copper/10 px-3 py-1.5 text-sm text-copper"
              >
                <button type="button" onClick={() => applySavedView(view)} className="font-semibold">
                  {view.name}
                </button>
                <button
                  type="button"
                  onClick={() => void deleteSavedView(view.id)}
                  aria-label={t("search.deleteView")}
                  className="opacity-70 hover:opacity-100"
                >
                  <XMarkIcon aria-hidden="true" className="h-3.5 w-3.5" />
                </button>
              </span>
            ))}
          </div>
        )}
      </section>

      {activeFilters.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {activeFilters.map((filter) => (
            <button
              key={filter.key}
              type="button"
              onClick={filter.onRemove}
              className="flex items-center gap-1.5 rounded-full border border-line-strong px-3 py-1 text-xs font-medium"
            >
              {filter.label}
              <XMarkIcon aria-hidden="true" className="h-3.5 w-3.5" />
            </button>
          ))}
        </div>
      )}

      {error && (
        <p role="alert" className="rounded-lg bg-danger-soft p-3 text-sm text-danger">
          {error}
        </p>
      )}

      {failures.length > 0 && (
        <div className="rounded-lg border border-warning/40 bg-warning-soft p-3 text-sm text-warning">
          <p className="font-semibold">{t("search.bulkFailuresTitle")}</p>
          <ul className="mt-1 list-disc space-y-0.5 pl-5">
            {failures.map((failure) => (
              <li key={`${failure.kind}-${failure.id}`}>
                {t(`search.kinds.${failure.kind}`)} — {failure.reason}
              </li>
            ))}
          </ul>
        </div>
      )}

      {selected.size > 0 && (
        <div className="sticky top-0 z-10 flex flex-wrap items-center gap-2 rounded-xl border border-copper/30 bg-copper/5 p-3 text-sm">
          <span className="font-semibold">{t("search.selectedCount", { count: selected.size })}</span>
          <button
            type="button"
            disabled={busy}
            onClick={confirmDelete}
            className="rounded-lg border border-danger/40 px-3 py-1.5 font-semibold text-danger disabled:opacity-50"
          >
            {t("search.bulkDelete")}
          </button>
          <button
            type="button"
            disabled={busy}
            onClick={() => void runBulk("duplicate")}
            className="rounded-lg border border-line px-3 py-1.5 font-semibold disabled:opacity-50"
          >
            {t("search.bulkDuplicate")}
          </button>
          <select
            value={moveTarget}
            onChange={(event) => setMoveTarget(event.target.value)}
            className="rounded-lg border border-line px-2 py-1.5 bg-raised"
          >
            <option value="">{t("search.bulkMoveTarget")}</option>
            {vehicleList?.map((vehicle) => (
              <option key={vehicle.id} value={vehicle.id}>
                {vehicle.name}
              </option>
            ))}
          </select>
          <button
            type="button"
            disabled={busy || !moveTarget}
            onClick={confirmMove}
            className="rounded-lg border border-line px-3 py-1.5 font-semibold disabled:opacity-50"
          >
            {t("search.bulkMove")}
          </button>
          <button
            type="button"
            disabled={busy}
            onClick={() => void exportSelected()}
            className="ml-auto rounded-lg bg-copper px-3 py-1.5 font-semibold text-white disabled:opacity-50"
          >
            {t("search.bulkExport")}
          </button>
        </div>
      )}

      {results === null ? (
        <Skeleton lines={6} />
      ) : results.length === 0 ? (
        <p className="rounded-xl border border-dashed p-8 text-center text-sm text-graphite/50">
          {t("search.empty")}
        </p>
      ) : (
        <div className="space-y-2">
          {results.map((item) => {
            const key = `${item.kind}-${item.id}`;
            const KindIcon = NAV_ICONS[item.kind];
            return (
              <div
                key={key}
                className="flex min-w-0 items-start gap-3 rounded-xl border border-line bg-raised p-4 shadow-sm"
              >
                <input
                  type="checkbox"
                  className="mt-1 shrink-0"
                  checked={selected.has(key)}
                  onChange={() => toggleSelected(key)}
                  aria-label={item.title}
                />
                <Link to={item.url} className="flex min-w-0 flex-1 items-start gap-3">
                  <span className="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-copper/10 text-brand dark:bg-copper/20">
                    <KindIcon aria-hidden="true" className="h-4 w-4" />
                  </span>
                  <span className="shrink-0 rounded-full bg-copper/10 px-2 py-1 text-[10px] font-bold uppercase text-copper">
                    {t(`search.kinds.${item.kind}`)}
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block break-words font-semibold text-ink">
                      {item.title}
                    </span>
                    {item.subtitle && (
                      <span className="mt-0.5 block line-clamp-2 break-words text-sm text-ink-subtle">
                        {item.subtitle}
                      </span>
                    )}
                    {item.tags.length > 0 && (
                      <span className="mt-1.5 flex flex-wrap gap-1">
                        {item.tags.map((tag) => (
                          <TagChip key={tag.id} tag={tag} />
                        ))}
                      </span>
                    )}
                    {item.occurred_on && (
                      <span className="mt-1 block text-xs text-ink-subtle">
                        {new Intl.DateTimeFormat(i18n.language).format(new Date(item.occurred_on))}
                      </span>
                    )}
                  </span>
                </Link>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
