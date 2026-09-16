import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { expect, it, vi } from "vitest";
import "../lib/i18n";
import { Dashboard } from "./Dashboard";
import { vehicles } from "../lib/api";

vi.mock("../lib/session", () => ({ useSession: () => ({ me: null }) }));

it("lets a new household create its first vehicle instead of loading forever", async () => {
  vi.spyOn(vehicles, "list").mockResolvedValue([]);
  render(<MemoryRouter><Dashboard /></MemoryRouter>);
  const link = await screen.findByRole("link");
  expect(link).toHaveAttribute("href", "/garage?new=1");
});
