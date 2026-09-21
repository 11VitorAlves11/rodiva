/** Capture the real UI with fictional records in a disposable local instance.
 * Run from frontend/: node scripts/readme-screenshots.mjs
 * See docs/SCREENSHOTS.md for setup and outputs.
 */
import { chromium, devices } from '@playwright/test';
import { mkdir } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';

const baseURL = process.env.SCREENSHOT_BASE_URL ?? 'http://127.0.0.1:15173';
if (!['127.0.0.1', 'localhost', '[::1]'].includes(new URL(baseURL).hostname)) {
  throw new Error('Use a disposable local instance for README screenshots.');
}
const output = fileURLToPath(new URL('../../docs/images/', import.meta.url));
await mkdir(output, { recursive: true });
// Chromium renders <input type="date"> in its own UI language, not the page locale, so a
// default launch would put mm/dd/yyyy in every form of a European Portuguese gallery.
// It reads that language from LANG; --lang alone translates the chrome and not the input.
const browser = await chromium.launch({ args: ['--lang=pt-PT'], env: { ...process.env, LANG: 'pt_PT.UTF-8' } });
try {
  const context = await browser.newContext({ baseURL, viewport: { width: 1440, height: 1000 }, deviceScaleFactor: 1, locale: 'pt-PT', timezoneId: 'Europe/Lisbon', colorScheme: 'light' });
  const call = async (path, data, method = 'POST') => {
    const response = await context.request.fetch(path, { method, data });
    if (!response.ok()) throw new Error(`${method} ${path}: ${response.status()} ${await response.text()}`);
    return response.json();
  };
  await call('/auth/register', { email: `readme-${Date.now()}@example.com`, password: 'local-demo-password-only', name: 'Ana', household_name: 'Garagem da família' });
  const car = await call('/api/vehicles', { name: 'O nosso familiar', make: 'Volvo', model: 'V60', year: 2021, license_plate: 'DE-MO-01', energy_type: 'diesel', initial_odometer: 72400 });
  const city = await call('/api/vehicles', { name: 'Pela cidade', make: 'Renault', model: 'Clio', year: 2022, license_plate: 'DE-MO-02', energy_type: 'petrol' });
  const today = new Date();
  const monthDate = (offset, day) => {
    const date = new Date(Date.UTC(today.getFullYear(), today.getMonth() + offset, day));
    return date.toISOString().slice(0, 10);
  };
  let reading = 72400;
  for (let month = -5; month <= 0; month++) {
    for (const day of [4, 16]) {
      reading += 640;
      await call(`/api/vehicles/${car.id}/fuel-records`, { recorded_on: monthDate(month, day), odometer_reading: reading, volume_litres: [39.8, 41.2, 40.6, 38.9, 42.1, 40.3][month + 5], unit_price: '1.659', full_tank: true, fuel_type: 'Gasóleo', station: day === 4 ? 'Posto da cidade' : 'Estação da viagem' });
    }
    await call(`/api/vehicles/${car.id}/expenses`, { issued_on: monthDate(month, 10), category: 'tolls', amount: [18.4, 27.6, 14.2, 38.8, 21.5, 12.3][month + 5], supplier: 'Via Verde', status: 'paid' });
  }
  await call(`/api/vehicles/${car.id}/work-records`, { recorded_on: monthDate(-2, 20), kind: 'maintenance', description: 'Revisão anual · óleo e filtros', total_cost: 245, supplier: 'Oficina da família' });
  await call(`/api/vehicles/${car.id}/work-records`, { recorded_on: monthDate(0, 18), kind: 'maintenance', description: 'Alinhamento da direção', total_cost: 35, supplier: 'Oficina da família' });
  await call(`/api/vehicles/${car.id}/odometer-readings`, { recorded_on: monthDate(0, 20), reading: reading + 180 });
  await call(`/api/vehicles/${car.id}/reminders`, { title: 'Inspeção periódica', due_date: monthDate(1, 12), repeat_days: 365 });
  await call(`/api/vehicles/${car.id}/reminders`, { title: 'Revisão e mudança de óleo', due_odometer: 90000, repeat_distance: 15000 });
  await call(`/api/vehicles/${car.id}/reminders`, { title: 'Renovar o seguro', due_date: monthDate(2, 5), repeat_days: 365 });
  // No separate odometer reading for this one: the history derives one from the fill-up,
  // and a second at the same reading would show up as a duplicate row.
  await call(`/api/vehicles/${city.id}/fuel-records`,{ recorded_on: monthDate(0, 15), odometer_reading: 28450, volume_litres: 32, total_price: 56.64, full_tank: true, fuel_type: 'Gasolina' });
  const page = await context.newPage();
  const capture = async (target, path, ready, name) => {
    await target.goto(path);
    await target.getByText(ready, { exact: true }).first().waitFor();
    await target.waitForLoadState('networkidle');
    await target.evaluate(() => document.fonts.ready);
    // scrollIntoViewIfNeeded leaves a partly visible element alone, which framed both
    // mobile shots on the form above the subject. Put the subject at the top instead.
    const toTop = (el, above) => { el.scrollIntoView({ block: 'start' }); window.scrollBy(0, -above); };
    if (name === 'mobile-history') await target.locator('main ul > li').first().evaluate(toTop, 8);
    // Enough room above the form for the section that explains what it records.
    if (name === 'mobile-fuel') await target.locator('main form').evaluate(toTop, 190);
    const overflow = await target.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth);
    if (overflow) console.log(await target.evaluate(() => ({width:document.documentElement.clientWidth, scroll:document.documentElement.scrollWidth, elements:[...document.querySelectorAll('main *')].filter(el => el.getBoundingClientRect().right > document.documentElement.clientWidth + 1 && !el.closest('nav')).slice(0, 15).map(el => ({tag: el.tagName, cls: el.className, right: el.getBoundingClientRect().right, width: el.getBoundingClientRect().width}))})));
    if (overflow) throw new Error(`Horizontal overflow on ${name}`);
    await target.screenshot({ path: `${output}${name}.png`, animations: 'disabled' });
    console.log(`Captured ${name}`);
  };
  await capture(page, '/', 'O nosso familiar', 'desktop-dashboard');
  await capture(page, '/reports', 'Relatórios', 'desktop-reports');
  await page.emulateMedia({ colorScheme: 'dark' });
  await capture(page, '/', 'O nosso familiar', 'desktop-dark');

  const mobile = await browser.newContext({ ...devices['iPhone 13'], viewport: { width: 390, height: 844 }, screen: { width: 390, height: 844 }, baseURL, deviceScaleFactor: 2, locale: 'pt-PT', timezoneId: 'Europe/Lisbon', colorScheme: 'light', storageState: await context.storageState() });
  const phone = await mobile.newPage();
  await capture(phone, '/', 'O nosso familiar', 'mobile-dashboard');
  await capture(phone, '/history', 'Alinhamento da direção', 'mobile-history');
  await capture(phone, `/vehicles/${car.id}?section=fuel&new=1`, 'Litros', 'mobile-fuel');
  await mobile.close();
  await context.close();
} finally {
  await browser.close();
}
