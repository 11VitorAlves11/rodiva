import { render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, expect, it, vi } from "vitest";
import "../lib/i18n";
import { Reports } from "./Reports";

const summary = {
  date_from: null,
  date_to: null,
  currency: "EUR",
  total_cost: "1275.40",
  total_distance: 7220,
  inventory_value: "0.00",
  overdue_reminders: 0,
  vehicles: [
    {
      vehicle_id: "a",
      vehicle_name: "O nosso familiar",
      distance_unit: "km",
      total_cost: "1218.76",
      distance: 7220,
      cost_per_distance: "0.17",
      consumption_average: "6.335",
      consumption_minimum: "6.078",
      consumption_maximum: "6.578",
      categories: [
        { category: "expense:tolls", amount: "132.80" },
        { category: "expense:consumíveis", amount: "12.00" },
        { category: "fuel", amount: "805.96" },
        { category: "work:maintenance", amount: "280.00" },
      ],
      monthly: [],
    },
  ],
};

function stub(report: unknown = summary, vehicleList: unknown[] = [{ id: "a", name: "O nosso familiar" }]) {
  vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input);
    const data = url.includes("/reports/summary") ? report : vehicleList;
    return new Response(JSON.stringify(data), { status: 200 });
  }));
}

beforeEach(() => stub());

it("reads the consumption metrics as numbers with a unit, not raw API strings", async () => {
  render(<MemoryRouter><Reports /></MemoryRouter>);

  expect(await screen.findByText("6,3 L/100 km")).toBeInTheDocument();
  expect(screen.getByText("6,1 L/100 km")).toBeInTheDocument();
  expect(screen.getByText("6,6 L/100 km")).toBeInTheDocument();
  expect(screen.queryByText("6.335")).not.toBeInTheDocument();
});

it("names each category instead of showing the API key", async () => {
  render(<MemoryRouter><Reports /></MemoryRouter>);

  // "Combustível" also heads a column of the monthly table, so read the breakdown itself.
  const breakdown = within((await screen.findByText("Categorias")).parentElement!);
  expect(breakdown.getByText("Portagens")).toBeInTheDocument();
  expect(breakdown.getByText("Combustível")).toBeInTheDocument();
  expect(breakdown.getByText("Manutenção")).toBeInTheDocument();
  // An expense category is free text, so an unknown one is shown as the household wrote it.
  expect(breakdown.getByText("consumíveis")).toBeInTheDocument();
  expect(screen.queryByText("expense:tolls")).not.toBeInTheDocument();
});

it("gives the household distance a unit only when the vehicles agree on one", async () => {
  const { unmount } = render(<MemoryRouter><Reports /></MemoryRouter>);
  expect(await screen.findByText("7220 km")).toBeInTheDocument();
  unmount();

  const mixed = {
    ...summary,
    vehicles: [summary.vehicles[0], { ...summary.vehicles[0], vehicle_id: "b", vehicle_name: "Importado", distance_unit: "mi" }],
  };
  stub(mixed, [{ id: "a", name: "O nosso familiar" }, { id: "b", name: "Importado" }]);
  render(<MemoryRouter><Reports /></MemoryRouter>);

  expect(await screen.findByText("7220")).toBeInTheDocument();
  expect(screen.queryByText("7220 km")).not.toBeInTheDocument();
});
