import { useState } from "react";
import type { FormEvent } from "react";
import { useTranslation } from "react-i18next";

import { notes } from "../../lib/api";
import { ApiError } from "../../lib/api/client";
import type { Note } from "../../lib/api/types";

export function NotesSection({ records, vehicleId, onCreated }: { records: Note[]; vehicleId: string; onCreated: () => void }) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [pinned, setPinned] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  async function submit(event: FormEvent) {
    event.preventDefault(); setSaving(true); setError(null);
    try { await notes.create(vehicleId, { title, content, pinned }); setOpen(false); setTitle(""); setContent(""); onCreated(); }
    catch (cause) { setError(cause instanceof ApiError ? cause.message : t("common.error")); }
    finally { setSaving(false); }
  }
  return <section className="space-y-4 rounded-xl border border-slate-200 bg-white p-4 shadow-sm sm:p-6"><div className="flex items-center justify-between gap-4"><div><h2 className="text-lg font-semibold text-slate-900">{t("notes.title")}</h2><p className="text-sm text-slate-500">{t("notes.description")}</p></div><button onClick={() => setOpen((value) => !value)} className="rounded-lg bg-copper px-3 py-2 text-sm font-semibold text-white">{t("notes.add")}</button></div>{open && <form onSubmit={submit} className="space-y-3 rounded-lg bg-slate-50 p-4"><input required placeholder={t("notes.name")} value={title} onChange={(event) => setTitle(event.target.value)} className="w-full rounded-lg border border-slate-300 px-3 py-2.5" /><textarea required rows={5} placeholder={t("notes.content")} value={content} onChange={(event) => setContent(event.target.value)} className="w-full resize-y rounded-lg border border-slate-300 bg-white px-3 py-2.5" /><label className="flex items-center gap-2 text-sm text-slate-700"><input type="checkbox" checked={pinned} onChange={(event) => setPinned(event.target.checked)} />{t("notes.pin")}</label>{error && <p className="text-sm text-red-700">{error}</p>}<button disabled={saving} className="rounded-lg bg-copper px-4 py-2 text-sm font-semibold text-white disabled:opacity-50">{t("garage.save")}</button></form>}{records.length === 0 ? <p className="py-4 text-sm text-slate-500">{t("notes.empty")}</p> : <div className="grid gap-3 sm:grid-cols-2">{records.map((note) => <article key={note.id} className="rounded-lg border border-slate-200 bg-slate-50 p-4"><div className="flex gap-2"><h3 className="font-semibold text-slate-900">{note.title}</h3>{note.pinned && <span title={t("notes.pinned")}>●</span>}</div><p className="mt-2 whitespace-pre-wrap text-sm text-slate-600">{note.content}</p></article>)}</div>}</section>;
}
