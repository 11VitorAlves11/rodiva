import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, expect, it, vi } from "vitest";
import "../lib/i18n";
import { attachments, expenses, fuel, notes, odometer, tags, vehicles, workRecords } from "../lib/api";
import { ApiError } from "../lib/api/client";
import type { Vehicle as VehicleType } from "../lib/api/types";
import { Vehicle } from "./Vehicle";

vi.mock("../lib/session", () => ({
  useSession: () => ({ me: { membership: { role: "owner" } } }),
}));
vi.mock("../components/ui/confirm-context", () => ({ useConfirm: () => vi.fn() }));

const vehicle = {
  id: "v", name: "Volvo", distance_unit: "km", photo_url: "/storage/vehicles/v.jpg",
  status: "active", energy_type: "petrol", odometer_offset: 0, odometer_multiplier: "1.0",
} as VehicleType;

beforeEach(() => {
  vi.spyOn(vehicles, "get").mockResolvedValue(vehicle);
  for (const resource of [attachments, expenses, fuel, notes, odometer, workRecords, tags]) {
    vi.spyOn(resource, "list").mockResolvedValue([]);
  }
  vi.spyOn(tags, "forRecord").mockResolvedValue([]);
});

async function show() {
  const view = render(
    <MemoryRouter initialEntries={["/vehicles/v"]}>
      <Routes><Route path="/vehicles/:vehicleId" element={<Vehicle />} /></Routes>
    </MemoryRouter>,
  );
  const input = await screen.findByLabelText("Alterar fotografia");
  return { ...view, input };
}

it("allows gallery selection and refreshes the image after replacing it", async () => {
  let finish!: (value: VehicleType) => void;
  const upload = vi.spyOn(vehicles, "uploadPhoto").mockImplementation(
    () => new Promise((resolve) => { finish = resolve; }),
  );
  const { input, container } = await show();
  expect(input).not.toHaveAttribute("capture");
  const oldSrc = container.querySelector("img")!.src;
  await userEvent.upload(input, new File(["photo"], "car.jpg", { type: "image/jpeg" }));
  await waitFor(() => expect(upload).toHaveBeenCalledWith("v", {
    content_type: "image/jpeg", content_base64: "cGhvdG8=",
  }));
  expect(input).toBeDisabled();
  finish(vehicle);
  await waitFor(() => expect(input).toBeEnabled());
  expect(container.querySelector("img")!.src).not.toBe(oldSrc);
});

it("keeps unsaved edits after an upload failure and allows retrying the same file", async () => {
  const upload = vi.spyOn(vehicles, "uploadPhoto")
    .mockRejectedValueOnce(new ApiError(413, "Image is too large"))
    .mockResolvedValue(vehicle);
  const { input } = await show();
  fireEvent.click(screen.getByRole("button", { name: "Editar" }));
  const name = screen.getByDisplayValue("Volvo");
  fireEvent.change(name, { target: { value: "Novo nome" } });
  const file = new File(["photo"], "car.jpg", { type: "image/jpeg" });
  await userEvent.upload(input, file);
  expect(await screen.findByRole("alert")).toHaveTextContent("Image is too large");
  expect(name).toHaveValue("Novo nome");
  await userEvent.upload(input, file);
  await waitFor(() => expect(upload).toHaveBeenCalledTimes(2));
  await waitFor(() => expect(input).toBeEnabled());
  expect(screen.queryByRole("alert")).not.toBeInTheDocument();
});

it("handles file reading failures without leaving the upload disabled", async () => {
  const upload = vi.spyOn(vehicles, "uploadPhoto");
  vi.spyOn(FileReader.prototype, "readAsDataURL").mockImplementation(function (this: FileReader) {
    this.dispatchEvent(new ProgressEvent("error"));
  });
  const { input } = await show();
  await userEvent.upload(input, new File(["photo"], "car.jpg", { type: "image/jpeg" }));
  expect(await screen.findByRole("alert")).toBeInTheDocument();
  expect(input).toBeEnabled();
  expect(upload).not.toHaveBeenCalled();
  expect(screen.getByRole("heading", { name: "Volvo" })).toBeInTheDocument();
});
