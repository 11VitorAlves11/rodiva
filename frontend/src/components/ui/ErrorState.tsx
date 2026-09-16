import { useTranslation } from "react-i18next";

export function ErrorState({ onRetry }: { onRetry: () => void }) {
  const { t } = useTranslation();
  return (
    <div className="rounded-md border border-danger/40 bg-red-50 p-4 text-sm text-danger">
      <p>{t("common.error")}</p>
      <button onClick={onRetry} className="mt-2 font-medium underline">
        Tentar novamente
      </button>
    </div>
  );
}
