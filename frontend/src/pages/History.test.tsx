import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter, useLocation } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import "../lib/i18n";
import { History } from "./History";

function Location() { return <output data-testid="location">{useLocation().search}</output>; }
function show(path = "/history") {
  return render(<MemoryRouter initialEntries={[path]}><History /><Location /></MemoryRouter>);
}

beforeEach(() => {
  vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input);
    const data = url.endsWith("/vehicles") ? [
      { id: "a", name: "Clássico", distance_unit: "mi" },
      { id: "b", name: "Carrinha", distance_unit: "km" },
    ] : url.endsWith("/a/work-records") ? [
      { id: "w1", recorded_on: "2026-01-10", description: "Revisão antiga", total_cost: "0.00" },
      { id: "w2", recorded_on: "2026-02-10", description: "Revisão recente", total_cost: "45.50" },
    ] : url.endsWith("/b/work-records") ? [
      { id: "w3", recorded_on: "2026-02-10", description: "Travões", total_cost: "100.00" },
    ] : url.endsWith("/a/odometer-readings") ? [
      { id: "o1", recorded_on: "2026-02-10", reading: 500 },
    ] : [];
    return new Response(JSON.stringify(data), { status: 200 });
  }));
});

describe("History", () => {
  it("combines URL filters and includes both date boundaries", async () => {
    show("/history?type=work&vehicle=a&from=2026-02-10&to=2026-02-10&q=revisao");
    expect(await screen.findByText("Revisão recente")).toBeInTheDocument();
    expect(screen.queryByText("Revisão antiga")).not.toBeInTheDocument();
    expect(screen.queryByText("Travões")).not.toBeInTheDocument();
    expect(screen.getByText("1 registo")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Tipo de registo"), { target: { value: "all" } });
    expect(screen.getByTestId("location")).toHaveTextContent("vehicle=a&from=2026-02-10&to=2026-02-10&q=revisao");
  });

  it("sorts by date, preserves miles, and formats zero costs", async () => {
    show("/history?vehicle=a&sort=asc");
    await screen.findByText("Revisão antiga");
    expect(screen.getAllByRole("link")[0]).toHaveTextContent("Revisão antiga");
    expect(screen.getAllByRole("link")[0]).toHaveTextContent(/0,00/);
    expect(screen.getByText("500 mi")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Ordenar por"), { target: { value: "desc" } });
    expect(screen.getAllByRole("link")[0]).toHaveTextContent("Revisão recente");
  });

  it("clears filters without losing unrelated parameters", async () => {
    show("/history?type=work&vehicle=a&from=2026-03-10&to=2026-01-10&source=dashboard");
    expect(await screen.findByRole("alert")).toHaveTextContent("A data final");
    fireEvent.click(screen.getByText("Limpar filtros"));
    expect(screen.getByTestId("location")).toHaveTextContent("?source=dashboard");
    expect(screen.getAllByRole("link")).toHaveLength(4);
  });

  it("allows retrying a failed request", async () => {
    vi.mocked(fetch).mockRejectedValueOnce(new Error("Offline"));
    show();
    fireEvent.click(await screen.findByRole("button"));
    expect(await screen.findByText("Revisão antiga")).toBeInTheDocument();
  });
});
