import { createContext, useContext } from "react";

export type ConfirmRequest = {
  message: string;
  confirmLabel?: string;
  tone?: "danger" | "default";
  /** Present for the prompt variant: the dialog collects a line of text. */
  input?: { label: string; initial?: string; maxLength?: number };
};

export type Ask = (request: ConfirmRequest | string) => Promise<boolean>;

/** Resolves to the text entered, or null if the member backed out. */
export type AskText = (
  request: ConfirmRequest & { input: NonNullable<ConfirmRequest["input"]> },
) => Promise<string | null>;

export const ConfirmContext = createContext<{ ask: Ask; askText: AskText } | null>(null);

export function useConfirm(): Ask {
  const context = useContext(ConfirmContext);
  if (!context) throw new Error("useConfirm must be used inside a ConfirmProvider");
  return context.ask;
}

export function useAskText(): AskText {
  const context = useContext(ConfirmContext);
  if (!context) throw new Error("useAskText must be used inside a ConfirmProvider");
  return context.askText;
}
