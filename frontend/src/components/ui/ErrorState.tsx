import { useTranslation } from "react-i18next";

export function ErrorState({ onRetry }: { onRetry: () => void }) {
  const { t } = useTranslation();
  return (
    <div className="rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-800">
      <p>{t("common.error")}</p>
      <button onClick={onRetry} className="mt-2 font-medium underline">
        Tentar novamente
      </button>
    </div>
  );
}
