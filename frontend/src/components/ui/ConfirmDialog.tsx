import { useCallback, useEffect, useRef, useState } from "react";
import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";

import { Button } from "./Button";
import { ConfirmContext } from "./confirm-context";
import type { Ask, AskText, ConfirmRequest } from "./confirm-context";

/**
 * Replaces `window.confirm`, which the app used in twenty-odd places.
 *
 * The native dialog ignores the theme, cannot be translated beyond its message,
 * sizes its buttons for a mouse rather than a thumb, and in an installed PWA on
 * iOS announces the origin above the question. A `<dialog>` fixes all of that
 * and keeps the same shape at the call site: await it, and act on the answer.
 */

export function ConfirmProvider({ children }: { children: ReactNode }) {
  const { t } = useTranslation();
  const [request, setRequest] = useState<ConfirmRequest | null>(null);
  const [text, setText] = useState("");
  const dialogRef = useRef<HTMLDialogElement>(null);
  const resolveRef = useRef<((answer: boolean | string | null) => void) | null>(null);
  const wantsTextRef = useRef(false);

  const ask = useCallback<Ask>((incoming) => {
    const next = typeof incoming === "string" ? { message: incoming } : incoming;
    wantsTextRef.current = false;
    setText("");
    setRequest(next);
    return new Promise<boolean>((resolve) => {
      resolveRef.current = resolve as (answer: boolean | string | null) => void;
    });
  }, []);

  const askText = useCallback<AskText>((incoming) => {
    wantsTextRef.current = true;
    setText(incoming.input.initial ?? "");
    setRequest(incoming);
    return new Promise<string | null>((resolve) => {
      resolveRef.current = resolve as (answer: boolean | string | null) => void;
    });
  }, []);

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;
    if (request) dialog.showModal();
    else if (dialog.open) dialog.close();
  }, [request]);

  const settle = (accepted: boolean) => {
    const answer = wantsTextRef.current ? (accepted ? text : null) : accepted;
    resolveRef.current?.(answer);
    resolveRef.current = null;
    setRequest(null);
  };

  return (
    <ConfirmContext.Provider value={{ ask, askText }}>
      {children}
      <dialog
        ref={dialogRef}
        // Escape and the backdrop both mean "no", so a dismissed dialog never
        // leaves the caller waiting on a promise that resolves to nothing.
        onCancel={(event) => {
          event.preventDefault();
          settle(false);
        }}
        onClose={() => resolveRef.current && settle(false)}
        className="m-auto max-w-sm rounded-xl border border-line bg-raised p-0 text-ink shadow-xl backdrop:bg-black/40"
      >
        {request && (
          <form
            method="dialog"
            className="p-5"
            onSubmit={(event) => {
              event.preventDefault();
              settle(true);
            }}
          >
            <p className="text-sm text-ink">{request.message}</p>
            {request.input && (
              <label className="mt-3 block text-sm">
                <span className="mb-1 block font-medium text-ink-muted">
                  {request.input.label}
                </span>
                <input
                  autoFocus
                  required
                  maxLength={request.input.maxLength ?? 120}
                  value={text}
                  onChange={(event) => setText(event.target.value)}
                  className="w-full rounded-lg border border-line bg-raised px-3 py-2"
                />
              </label>
            )}
            <div className="mt-5 flex justify-end gap-2">
              <Button variant="secondary" size="sm" onClick={() => settle(false)}>
                {t("common.cancel")}
              </Button>
              <Button
                type="submit"
                variant={request.tone === "danger" ? "danger" : "primary"}
                size="sm"
                autoFocus={!request.input}
              >
                {request.confirmLabel ?? t("common.confirm")}
              </Button>
            </div>
          </form>
        )}
      </dialog>
    </ConfirmContext.Provider>
  );
}

