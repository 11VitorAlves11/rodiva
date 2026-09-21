import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { expect, it, vi } from "vitest";
import "../lib/i18n";
import { Dashboard } from "./Dashboard";
import { charging, expenses, fuel, odometer, reminders, vehicles, workRecords } from "../lib/api";

vi.mock("../lib/session", () => ({ useSession: () => ({ me: null }) }));

it("lets a new household create its first vehicle instead of loading forever", async () => {
  vi.spyOn(vehicles, "list").mockResolvedValue([]);
  render(<MemoryRouter><Dashboard /></MemoryRouter>);
  const link = await screen.findByRole("link");
  expect(link).toHaveAttribute("href", "/garage?new=1");
});

it("writes a reminder's due date the way the locale does, not the way the API sends it", async () => {
  vi.spyOn(vehicles, "list").mockResolvedValue([{ id: "v", name: "Volvo", distance_unit: "km" } as never]);
  for (const resource of [fuel, charging, workRecords, expenses, odometer]) {
    vi.spyOn(resource, "list").mockResolvedValue([]);
  }
  vi.spyOn(reminders, "list").mockResolvedValue([
    { id: "r", title: "Inspeção periódica", due_date: "2026-10-12", status: "upcoming" } as never,
  ]);

  render(<MemoryRouter><Dashboard /></MemoryRouter>);

  expect(await screen.findByText("12/10/2026")).toBeInTheDocument();
  expect(screen.queryByText("2026-10-12")).not.toBeInTheDocument();
});
