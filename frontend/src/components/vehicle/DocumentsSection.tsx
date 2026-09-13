import { useState } from "react";
import { useTranslation } from "react-i18next";

import { attachments } from "../../lib/api";
import { ApiError } from "../../lib/api/client";
import type { Attachment } from "../../lib/api/types";

export function DocumentsSection({ records, vehicleId, onCreated }: { records: Attachment[]; vehicleId: string; onCreated: () => void }) {
  const { t, i18n } = useTranslation();
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  async function upload(file: File) {
    setUploading(true); setError(null);
    try {
      const dataUrl = await new Promise<string>((resolve, reject) => { const reader = new FileReader(); reader.onload = () => resolve(String(reader.result)); reader.onerror = () => reject(reader.error); reader.readAsDataURL(file); });
      await attachments.create(vehicleId, { filename: file.name, content_type: file.type, content_base64: dataUrl.split(",", 2)[1] });
      onCreated();
    } catch (cause) { setError(cause instanceof ApiError ? cause.message : t("common.error")); }
    finally { setUploading(false); }
  }
  return <section className="space-y-4 rounded-xl border border-slate-200 bg-white p-4 shadow-sm sm:p-6"><div className="flex items-center justify-between gap-4"><div><h2 className="text-lg font-semibold text-slate-900">{t("documents.title")}</h2><p className="text-sm text-slate-500">{t("documents.description")}</p></div><label className={`cursor-pointer rounded-lg bg-copper px-3 py-2 text-sm font-semibold text-white ${uploading ? "opacity-50" : ""}`}>{uploading ? t("documents.uploading") : t("documents.add")}<input disabled={uploading} type="file" accept="application/pdf,image/jpeg,image/png,image/webp" className="sr-only" onChange={(event) => { const file = event.target.files?.[0]; if (file) void upload(file); }} /></label></div>{error && <p className="text-sm text-red-700">{error}</p>}{records.length === 0 ? <p className="py-4 text-sm text-slate-500">{t("documents.empty")}</p> : <ul className="divide-y divide-slate-100">{records.map((document) => <li key={document.id} className="flex items-center justify-between gap-4 py-3"><a href={attachments.downloadUrl(vehicleId, document.id)} className="flex min-w-0 flex-1 items-center gap-3"><span className="grid h-10 w-10 shrink-0 place-items-center rounded-lg bg-copper/10 text-copper">▤</span><div className="min-w-0"><p className="truncate font-medium text-slate-900">{document.filename}</p><p className="text-xs text-slate-500">{(document.size / 1024).toLocaleString(i18n.language, { maximumFractionDigits: 1 })} KB</p></div></a><button onClick={() => { if (window.confirm(t("common.confirmDelete"))) void attachments.remove(vehicleId, document.id).then(onCreated); }} className="shrink-0 text-xs font-medium text-red-700">{t("common.delete")}</button></li>)}</ul>}</section>;
}
