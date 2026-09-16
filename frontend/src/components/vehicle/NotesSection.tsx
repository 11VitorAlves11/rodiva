import { useState } from "react";
import type { FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { notes } from "../../lib/api";
import { ApiError } from "../../lib/api/client";
import type { Note } from "../../lib/api/types";
import { useSession } from "../../lib/session";

export function NotesSection({ records, vehicleId, onCreated }: { records: Note[]; vehicleId: string; onCreated: () => void }) {
  const { t } = useTranslation();
  const { me } = useSession();
  const canWrite = me?.membership.role !== "reader";
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<string | null>(null);
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [pinned, setPinned] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const input = "mt-1 w-full rounded-lg border border-graphite/15 px-3 py-2 dark:border-white/15 dark:bg-surface-dark";

  async function submit(event: FormEvent) {
    event.preventDefault(); setSaving(true); setError(null);
    try {
      if (editing) await notes.update(vehicleId, editing, { title, content, pinned });
      else await notes.create(vehicleId, { title, content, pinned });
      setOpen(false); setEditing(null); onCreated();
    } catch (cause) { setError(cause instanceof ApiError ? cause.message : t("common.error")); }
    finally { setSaving(false); }
  }

  return <section className="space-y-4 rounded-xl border border-graphite/10 bg-white p-4 dark:border-white/10 dark:bg-surface-dark-raised">
    <div className="flex flex-wrap items-center justify-between gap-3"><div><h2 className="text-lg font-semibold">{t("notes.title")}</h2><p className="text-sm text-graphite/60 dark:text-cream/60">{t("notes.description")}</p></div>{canWrite && <button onClick={() => { setOpen(true); setEditing(null); setTitle(""); setContent(""); setPinned(false); }} className="rounded-lg bg-copper px-3 py-2 font-semibold text-white">{t("notes.add")}</button>}</div>
    {error && <p role="alert" className="text-sm text-red-700">{error}</p>}
    {open && <form onSubmit={submit} className="space-y-3">
      <label className="block text-sm">{t("notes.name")}<input required maxLength={300} value={title} onChange={(event) => setTitle(event.target.value)} className={input} /></label>
      <label className="block text-sm">{t("notes.content")}<textarea required maxLength={20000} rows={5} value={content} onChange={(event) => setContent(event.target.value)} className={input} /></label>
      <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={pinned} onChange={(event) => setPinned(event.target.checked)} />{t("notes.pin")}</label>
      <div className="flex gap-3"><button disabled={saving} className="rounded-lg bg-copper px-4 py-2 text-white disabled:opacity-60">{t("garage.save")}</button><button type="button" disabled={saving} onClick={() => setOpen(false)} className="rounded-lg border px-4 py-2">{t("common.cancel")}</button></div>
    </form>}
    {!records.length ? <p className="text-sm">{t("notes.empty")}</p> : <div className="grid gap-3 sm:grid-cols-2">{records.map((note) => <article key={note.id} className="min-w-0 rounded-lg border border-graphite/10 p-4 dark:border-white/10">
      <h3 className="break-words font-semibold">{note.title}{note.pinned && <span className="ml-2 text-xs text-copper">{t("notes.pinned")}</span>}</h3>
      <p className="mt-2 whitespace-pre-wrap break-words text-sm">{note.content}</p>
      {canWrite && <div className="mt-3 flex gap-3"><button disabled={saving} className="text-sm text-copper" onClick={() => { setEditing(note.id); setTitle(note.title); setContent(note.content); setPinned(note.pinned); setOpen(true); }}>{t("common.edit")}</button><button disabled={saving} className="text-sm text-red-700" onClick={() => {
        if (!window.confirm(t("common.confirmDelete"))) return;
        setSaving(true); setError(null);
        void notes.remove(vehicleId, note.id).then(() => { if (editing === note.id) setOpen(false); onCreated(); }).catch(() => setError(t("common.error"))).finally(() => setSaving(false));
      }}>{t("common.delete")}</button></div>}
    </article>)}</div>}
  </section>;
}
