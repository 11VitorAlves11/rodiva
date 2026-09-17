import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeAll, describe, expect, it, vi } from "vitest";
import "../lib/i18n";
import { ImportRecords } from "./ImportRecords";
import { ConfirmProvider } from "../components/ui/ConfirmDialog";
import { imports, vehicles } from "../lib/api";
import type { Vehicle } from "../lib/api/types";

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

function renderPage() {
  return render(
    <MemoryRouter>
      <ConfirmProvider>
        <ImportRecords />
      </ConfirmProvider>
    </MemoryRouter>,
  );
}

vi.mock("../lib/session", () => ({ useSession: () => ({ me: { membership: { role: "owner" } } }) }));
const result = { fields: ["title", "content"], columns: ["title", "content"], rows: [{ line: 2, data: { title: "Test", content: "Note" }, errors: [] }], errors: [], imported: 0 };

describe("ImportRecords", () => {
  it("requires a fresh preview after changes and confirms the import", async () => {
    vi.spyOn(vehicles, "list").mockResolvedValue([{ id: "a", name: "Car" } as Vehicle]);
    vi.spyOn(imports, "preview").mockResolvedValue(result);
    const commit = vi.spyOn(imports, "commit").mockResolvedValue({ ...result, imported: 1 });
    renderPage();
    await screen.findByText("Car");
    fireEvent.change(screen.getByLabelText("Tipo de registo"), { target: { value: "notes" } });
    fireEvent.change(screen.getByLabelText("Conteúdo do ficheiro (editável)"), { target: { value: "title,content\nTest,Note" } });
    fireEvent.click(screen.getByRole("button", { name: "Pré-visualizar e validar" }));
    expect(await screen.findByRole("button", { name: "Importar 1 registos" })).toBeEnabled();
    fireEvent.change(screen.getByLabelText("Título"), { target: { value: "content" } });
    expect(screen.queryByRole("button", { name: "Importar 1 registos" })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Pré-visualizar e validar" }));
    fireEvent.click(await screen.findByRole("button", { name: "Importar 1 registos" }));
    // The shared dialog replaced window.confirm, so the import is now agreed to
    // by answering it rather than by stubbing a browser built-in.
    fireEvent.click(await screen.findByRole("button", { name: "Confirmar" }));
    expect(await screen.findByText(/Importação concluída/)).toBeInTheDocument();
    expect(commit).toHaveBeenCalledWith(expect.objectContaining({ mapping: { title: "content" }, vehicle_id: "a" }));
    expect(screen.getByRole("button", { name: "Importar 1 registos" })).toBeDisabled();
  });

  it("does not allow committing an invalid preview", async () => {
    vi.spyOn(vehicles, "list").mockResolvedValue([{ id: "a", name: "Car" } as Vehicle]);
    vi.spyOn(imports, "preview").mockResolvedValue({ ...result, errors: ["Invalid odometer chronology"] });
    renderPage();
    await screen.findByText("Car");
    fireEvent.change(screen.getByLabelText("Conteúdo do ficheiro (editável)"), { target: { value: "test" } });
    fireEvent.click(screen.getByRole("button", { name: "Pré-visualizar e validar" }));
    expect(await screen.findByRole("button", { name: "Importar 1 registos" })).toBeDisabled();
  });
});
