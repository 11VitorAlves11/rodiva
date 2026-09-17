import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeAll, expect, it, vi } from "vitest";

import "../../lib/i18n";
import { ConfirmProvider } from "./ConfirmDialog";
import { useAskText, useConfirm } from "./confirm-context";

// jsdom knows the <dialog> element but not its modal behaviour.
beforeAll(() => {
  HTMLDialogElement.prototype.showModal = function showModal() {
    this.open = true;
  };
  HTMLDialogElement.prototype.close = function close() {
    this.open = false;
    this.dispatchEvent(new Event("close"));
  };
});

function Subject({ onAnswer }: { onAnswer: (answer: boolean) => void }) {
  const confirm = useConfirm();
  return (
    <button onClick={async () => onAnswer(await confirm("Eliminar este registo?"))}>
      delete
    </button>
  );
}

function TextSubject({ onAnswer }: { onAnswer: (answer: string | null) => void }) {
  const askText = useAskText();
  return (
    <button
      onClick={async () =>
        onAnswer(await askText({ message: "Guardar vista", input: { label: "Nome" } }))
      }
    >
      save
    </button>
  );
}

it("resolves true when the action is confirmed", async () => {
  const answer = vi.fn();
  render(
    <ConfirmProvider>
      <Subject onAnswer={answer} />
    </ConfirmProvider>,
  );

  await userEvent.click(screen.getByRole("button", { name: "delete" }));
  expect(await screen.findByText("Eliminar este registo?")).toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: "Confirmar" }));

  expect(answer).toHaveBeenCalledWith(true);
});

it("resolves false when it is cancelled", async () => {
  const answer = vi.fn();
  render(
    <ConfirmProvider>
      <Subject onAnswer={answer} />
    </ConfirmProvider>,
  );

  await userEvent.click(screen.getByRole("button", { name: "delete" }));
  await userEvent.click(await screen.findByRole("button", { name: "Cancelar" }));

  expect(answer).toHaveBeenCalledWith(false);
});

it("never leaves the caller waiting when the dialog is dismissed", async () => {
  /* A promise that resolves to nothing would freeze the action that awaited it. */
  const answer = vi.fn();
  render(
    <ConfirmProvider>
      <Subject onAnswer={answer} />
    </ConfirmProvider>,
  );

  await userEvent.click(screen.getByRole("button", { name: "delete" }));
  await screen.findByText("Eliminar este registo?");
  const dialog = document.querySelector("dialog") as HTMLDialogElement;
  dialog.close();

  await vi.waitFor(() => expect(answer).toHaveBeenCalledWith(false));
});

it("hands back the text that was typed", async () => {
  const answer = vi.fn();
  render(
    <ConfirmProvider>
      <TextSubject onAnswer={answer} />
    </ConfirmProvider>,
  );

  await userEvent.click(screen.getByRole("button", { name: "save" }));
  await userEvent.type(await screen.findByLabelText("Nome"), "Revisões por fazer");
  await userEvent.click(screen.getByRole("button", { name: "Confirmar" }));

  expect(answer).toHaveBeenCalledWith("Revisões por fazer");
});

it("hands back null when the text prompt is cancelled", async () => {
  const answer = vi.fn();
  render(
    <ConfirmProvider>
      <TextSubject onAnswer={answer} />
    </ConfirmProvider>,
  );

  await userEvent.click(screen.getByRole("button", { name: "save" }));
  await userEvent.type(await screen.findByLabelText("Nome"), "Descartado");
  await userEvent.click(screen.getByRole("button", { name: "Cancelar" }));

  expect(answer).toHaveBeenCalledWith(null);
});
