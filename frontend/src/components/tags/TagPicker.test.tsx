import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, it, vi } from "vitest";

import "../../lib/i18n";
import { tags as tagsApi } from "../../lib/api";
import type { Tag, TagUsage } from "../../lib/api/types";
import { TagPicker } from "./TagPicker";

const winter: TagUsage = {
  id: "tag-winter",
  name: "Inverno",
  color: "#2B5FA8",
  created_at: "2026-09-01T00:00:00Z",
  record_count: 3,
};
const warranty: TagUsage = {
  id: "tag-warranty",
  name: "Garantia",
  color: "#2F6F4E",
  created_at: "2026-09-01T00:00:00Z",
  record_count: 1,
};

beforeEach(() => {
  vi.restoreAllMocks();
});

it("shows the tags already on the record", async () => {
  vi.spyOn(tagsApi, "list").mockResolvedValue([winter, warranty]);
  vi.spyOn(tagsApi, "forRecord").mockResolvedValue([winter]);

  render(<TagPicker kind="vehicle" recordId="v1" canEdit />);

  expect(await screen.findByText("Inverno")).toBeInTheDocument();
  expect(screen.queryByText("Garantia")).not.toBeInTheDocument();
});

it("sends the full set, not just the tag that changed", async () => {
  vi.spyOn(tagsApi, "list").mockResolvedValue([winter, warranty]);
  vi.spyOn(tagsApi, "forRecord").mockResolvedValue([winter]);
  const save = vi
    .spyOn(tagsApi, "setForRecord")
    .mockResolvedValue([winter, warranty] as Tag[]);

  render(<TagPicker kind="vehicle" recordId="v1" canEdit />);
  await screen.findByText("Inverno");
  await userEvent.click(screen.getByRole("button", { name: "+ Etiqueta" }));
  await userEvent.click(await screen.findByRole("button", { name: /Garantia/ }));

  await waitFor(() =>
    expect(save).toHaveBeenCalledWith("vehicle", "v1", ["tag-winter", "tag-warranty"]),
  );
});

it("puts the tag back when saving fails", async () => {
  vi.spyOn(tagsApi, "list").mockResolvedValue([winter]);
  vi.spyOn(tagsApi, "forRecord").mockResolvedValue([winter]);
  vi.spyOn(tagsApi, "setForRecord").mockRejectedValue(new Error("nope"));

  render(<TagPicker kind="vehicle" recordId="v1" canEdit />);
  await userEvent.click(await screen.findByRole("button", { name: "Retirar Inverno" }));

  // The optimistic removal is undone, so the chip does not silently disappear
  // while the record still carries the tag on the server.
  expect(await screen.findByText("Inverno")).toBeInTheDocument();
  expect(screen.getByText("Não foi possível guardar as etiquetas.")).toBeInTheDocument();
});

it("offers no editing affordance to a reader", async () => {
  vi.spyOn(tagsApi, "list").mockResolvedValue([winter]);
  vi.spyOn(tagsApi, "forRecord").mockResolvedValue([winter]);

  render(<TagPicker kind="vehicle" recordId="v1" canEdit={false} />);

  expect(await screen.findByText("Inverno")).toBeInTheDocument();
  expect(screen.queryByRole("button")).not.toBeInTheDocument();
});
