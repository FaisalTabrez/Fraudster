// Keyless browser smoke against the packaged fixture-mode origin.
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';

const { chromium } = createRequire(new URL('../../apps/web/package.json', import.meta.url))('playwright');
const base = process.env.FRAUDSTER_BASE_URL || 'http://127.0.0.1:4173';
const allowedOrigin = new URL(base).origin;
const externalRequests = [];
const analysisRequests = [];
const browser = await chromium.launch({ headless: true });

try {
  const page = await browser.newPage({ viewport: { width: 390, height: 844 } });
  await page.route('**/*', route => {
    const url = new URL(route.request().url());
    if (url.origin !== allowedOrigin) {
      externalRequests.push(url.origin);
      return route.abort();
    }
    return route.continue();
  });
  page.on('request', request => {
    if (request.url().endsWith('/api/v1/analyze')) analysisRequests.push(request.postDataJSON());
  });

  await page.goto(base);
  await page.getByLabel('Paste the message exactly as received').fill('Synthetic request: send your OTP now.');
  await Promise.all([
    page.waitForResponse(response => response.url().endsWith('/api/v1/analyze') && response.ok()),
    page.getByRole('button', { name: 'Check this message' }).click(),
  ]);
  await page.getByText('Demo data', { exact: true }).waitFor();
  assert.equal(analysisRequests.length, 1);
  assert.equal(analysisRequests[0].text, 'Synthetic request: send your OTP now.');
  assert.equal(await page.getByRole('heading', { level: 2, name: /Pause/ }).evaluate(element => element === document.activeElement), true);
  assert.equal((await page.locator('body').innerText()).includes('0%'), false);

  await page.getByRole('button', { name: 'Link' }).click();
  await page.getByLabel(/One link per line/).fill('https://trusted.example@evil.test/pay');
  assert.equal(await page.getByRole('link').count(), 0);
  assert.equal(await page.locator('.fr-url__host').innerText(), 'evil.test');
  assert.equal(await page.getByText('Not opened', { exact: true }).count(), 1);
  assert.deepEqual(externalRequests, []);
  console.log('PASS fixture browser flow, focus, demo label, inert URL, and no external requests');
} finally {
  await browser.close();
}
