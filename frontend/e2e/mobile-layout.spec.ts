import { expect, test } from "@playwright/test";

/**
 * A phone-width page must not be wider than the phone. `body { overflow-x: clip }`
 * hides the scrollbar, so an overflowing element is invisible until something
 * anchored to the document width moves with it — which is how the hidden file
 * input on the vehicle page pushed the fixed bottom navigation off screen.
 *
 * Only an engine that lays the page out can see this, so it lives here and not
 * in the jsdom suite.
 */

const PASSWORD = "a-long-enough-password";

test.use({ viewport: { width: 390, height: 844 } });

test("no page is wider than the phone that shows it", async ({ page }) => {
  await page.goto("/login");
  await page.getByRole("button", { name: "Criar agregado" }).click();
  await page.getByLabel("Nome do agregado").fill("Agregado móvel");
  await page
    .getByLabel("Correio eletrónico")
    .fill(`e2e-mobile-${Date.now()}-${Math.floor(Math.random() * 10_000)}@example.com`);
  await page.getByLabel(/^Palavra-passe/).fill(PASSWORD);
  await page.getByRole("button", { name: "Criar conta e agregado" }).click();
  await expect(page).not.toHaveURL(/\/login/);

  await page.goto("/garage?new=1");
  await page.getByLabel(/^Nome/).fill("Volvo V60");
  await page.getByRole("button", { name: "Guardar" }).click();
  await page.getByRole("link", { name: "Volvo V60" }).click();
  await expect(page.getByRole("heading", { name: "Volvo V60" })).toBeVisible();

  for (const path of ["/", "/history", page.url()]) {
    await page.goto(path);
    await page.waitForLoadState("networkidle");
    const overflowing = await page.evaluate(() =>
      [...document.querySelectorAll("*")]
        .filter((el) => el.getBoundingClientRect().right > document.documentElement.clientWidth + 1)
        // A tab strip and a table scroll sideways inside their own box by design.
        .filter((el) => !el.closest("[class*='overflow-x-auto']"))
        .map((el) => `${el.tagName}.${String(el.className)}`),
    );
    expect(overflowing, path).toEqual([]);
  }
});
