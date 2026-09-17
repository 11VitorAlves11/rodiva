import { expect, test } from "@playwright/test";

/**
 * The journey the product exists for: sign up, put a vehicle in the garage,
 * record two full tanks, and read the consumption figure back.
 *
 * Nothing else covers this end to end — the unit tests each prove a piece,
 * and a break in the wiring between them would pass all of them.
 */

const PASSWORD = "a-long-enough-password";

function freshEmail(): string {
  return `e2e-${Date.now()}-${Math.floor(Math.random() * 10_000)}@example.com`;
}

test("a new household records two tanks and reads its consumption", async ({ page }) => {
  await page.goto("/login");

  await test.step("register a household", async () => {
    await page.getByRole("button", { name: "Criar agregado" }).click();
    await page.getByLabel("Nome do agregado").fill("Agregado E2E");
    await page.getByLabel("Correio eletrónico").fill(freshEmail());
    await page.getByLabel(/^Palavra-passe/).fill(PASSWORD);
    await page.getByRole("button", { name: "Criar conta e agregado" }).click();
    await expect(page).not.toHaveURL(/\/login/);
  });

  await test.step("put a vehicle in the garage", async () => {
    await page.goto("/garage?new=1");
    await page.getByLabel(/^Nome/).fill("Volvo V60");
    await page.getByRole("button", { name: "Guardar" }).click();
    await expect(page.getByRole("link", { name: "Volvo V60" })).toBeVisible();
  });

  await test.step("record two full tanks", async () => {
    await page.getByRole("link", { name: "Volvo V60" }).click();
    await expect(page.getByRole("heading", { name: "Volvo V60" })).toBeVisible();

    // `shown` is what the list renders it as: pt-PT writes a decimal with a comma.
    for (const fill of [
      { date: "2026-01-10", odometer: "10000", litres: "45", total: "76.50", shown: /45 L/ },
      {
        date: "2026-01-20",
        odometer: "10600",
        litres: "42.7",
        total: "73.10",
        shown: /42[.,]7 L/,
      },
    ]) {
      await page.getByRole("button", { name: "Registar abastecimento" }).click();
      await page.getByLabel("Data").fill(fill.date);
      await page.getByLabel("Odómetro (km)").fill(fill.odometer);
      await page.getByLabel("Litros").fill(fill.litres);
      await page.getByLabel("Total (€)").fill(fill.total);
      await page.getByRole("button", { name: "Guardar" }).click();
      await expect(page.getByText(fill.shown).first()).toBeVisible();
    }
  });

  await test.step("the consumption between the two tanks is shown", async () => {
    // 42.7 litres over 600 km is 7.117 l/100 km; the list rounds it for display.
    await expect(page.getByText(/7[.,]1\s*L\/100\s*km/)).toBeVisible();
  });
});

test("the sign-in screen refuses a wrong password", async ({ page }) => {
  const email = freshEmail();
  await page.goto("/login");
  await page.getByRole("button", { name: "Criar agregado" }).click();
  await page.getByLabel("Nome do agregado").fill("Agregado E2E");
  await page.getByLabel("Correio eletrónico").fill(email);
  await page.getByLabel(/^Palavra-passe/).fill(PASSWORD);
  await page.getByRole("button", { name: "Criar conta e agregado" }).click();
  await expect(page).not.toHaveURL(/\/login/);

  await page.context().clearCookies();
  await page.goto("/login");
  await page.getByLabel("Correio eletrónico").fill(email);
  await page.getByLabel(/^Palavra-passe/).fill("wrong-password-entirely");
  await page.getByRole("button", { name: "Entrar", exact: true }).click();

  await expect(page).toHaveURL(/\/login/);
});

test("a signed-out visitor is sent to the sign-in screen", async ({ page }) => {
  await page.context().clearCookies();
  await page.goto("/garage");

  await expect(page).toHaveURL(/\/login/);
});
