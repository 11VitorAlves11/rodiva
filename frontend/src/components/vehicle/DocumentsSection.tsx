import { useState } from "react";
import { useTranslation } from "react-i18next";
import { PaperClipIcon, TrashIcon } from "@heroicons/react/24/outline";

import { useSession } from "../../lib/session";
import { attachments } from "../../lib/api";
import { ApiError } from "../../lib/api/client";
import type { Attachment } from "../../lib/api/types";

export function DocumentsSection({
  records,
  vehicleId,
  onCreated,
}: {
  records: Attachment[];
  vehicleId: string;
  onCreated: () => void;
}) {
  const { t, i18n } = useTranslation();
  const { me } = useSession();
  const canWrite = me?.membership.role !== "reader";
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  async function upload(files: File[]) {
    setUploading(true); setError(null);
    const failures: string[] = [];
    let changed = false;
    for (const file of files) {
      try {
        const dataUrl = await new Promise<string>((resolve, reject) => {
          const reader = new FileReader();
          reader.onload = () => resolve(String(reader.result));
          reader.onerror = () => reject(reader.error);
          reader.readAsDataURL(file);
        });
        await attachments.create(vehicleId, { filename: file.name, content_type: file.type, content_base64: dataUrl.split(",", 2)[1] });
        changed = true;
      } catch (cause) { failures.push(`${file.name}: ${cause instanceof ApiError ? cause.message : t("common.error")}`); }
    }
    if (failures.length) setError(failures.join("; "));
    setUploading(false);
    if (changed) onCreated();
  }
  return (
    <section className="space-y-4 rounded-xl border border-line bg-raised p-4 shadow-sm sm:p-6">
      <div className="flex flex-col items-stretch gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-lg font-semibold text-ink">
            {t("documents.title")}
          </h2>
          <p className="text-sm text-slate-500">{t("documents.description")}</p>
        </div>
        {canWrite && <label
          role="button"
          className={`flex cursor-pointer items-center self-start rounded-lg bg-copper px-3 py-2 text-sm font-semibold text-white ${uploading ? "opacity-50" : ""}`}
        >
          {uploading ? t("documents.uploading") : t("documents.add")}
          <input
            disabled={uploading}
            type="file"
            multiple
            accept="application/pdf,image/jpeg,image/png,image/webp"
            className="sr-only"
            onChange={(event) => {
              const files = Array.from(event.target.files ?? []);
              event.target.value = "";
              if (files.length) void upload(files);
            }}
          />
        </label>}
      </div>
      {error && <p className="text-sm text-red-700">{error}</p>}
      {records.length === 0 ? (
        <p className="py-4 text-sm text-slate-500">{t("documents.empty")}</p>
      ) : (
        <ul className="divide-y divide-slate-100">
          {records.map((document) => (
            <li
              key={document.id}
              className="flex min-w-0 flex-col gap-2 py-3 min-[380px]:flex-row min-[380px]:items-center min-[380px]:justify-between min-[380px]:gap-4"
            >
              <a
                href={attachments.downloadUrl(vehicleId, document.id)}
                className="flex min-w-0 flex-1 items-center gap-3"
              >
                <span className="grid h-10 w-10 shrink-0 place-items-center rounded-lg bg-copper/10 text-copper">
                  <PaperClipIcon aria-hidden="true" className="h-5 w-5" />
                </span>
                <div className="min-w-0">
                  <p className="truncate font-medium text-ink">
                    {document.filename}
                  </p>
                  <p className="text-xs text-slate-500">
                    {(document.size / 1024).toLocaleString(i18n.language, {
                      maximumFractionDigits: 1,
                    })}{" "}
                    KB
                  </p>
                </div>
              </a>
              {canWrite && <button
                disabled={uploading}
                onClick={() => {
                  if (window.confirm(t("common.confirmDelete")))
                    void attachments
                      .remove(vehicleId, document.id)
                      .then(onCreated)
                      .catch(() => setError(t("common.error")));
                }}
                className="flex shrink-0 items-center gap-1 self-start text-xs font-medium text-red-700"
              >
                <TrashIcon aria-hidden="true" className="h-3.5 w-3.5" />
                {t("common.delete")}
              </button>}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
