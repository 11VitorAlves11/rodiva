import type { ReactNode } from "react";

/** An empty screen is an invitation to act, so the action sits inside it. */
export function EmptyState({
  title,
  description,
  action,
}: {
  title: ReactNode;
  description?: ReactNode;
  action?: ReactNode;
}) {
  return (
    <div className="rounded-xl border border-dashed border-line-strong px-6 py-10 text-center">
      <p className="text-sm font-semibold text-ink">{title}</p>
      {description && <p className="mx-auto mt-1 max-w-prose text-sm text-ink-muted">{description}</p>}
      {action && <div className="mt-4 flex justify-center">{action}</div>}
    </div>
  );
}
