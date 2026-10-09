// Opt-in browser smoke. See README; only generated synthetic inputs are used.
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
const { chromium } = createRequire(new URL('../../.venv/e2e/package.json', import.meta.url))('playwright');

const browser = await chromium.launch({ headless: true });
try {
  const page = await browser.newPage({ viewport: { width: 390, height: 844 } });
  const base = process.env.INGESTION_BASE_URL || 'http://127.0.0.1:5173';
  const allowedOrigin = new URL(base).origin;
  const requests = [];
  const external = [];
  await page.route('**/*', route => {
    if (new URL(route.request().url()).origin !== allowedOrigin) {
      external.push(true); return route.abort();
    }
    return route.continue();
  });
  page.on('request', request => {
    if (request.url().endsWith('/api/v1/analyze')) requests.push(request.postDataJSON());
  });
  await page.goto(base);
  const upload = page.getByLabel(/Upload PNG/);
  const button = page.getByRole('button', { name: 'Analyze reviewed content' });
  await upload.setInputFiles('.venv/ingestion-fixtures/synthetic-ocr.png');
  const correction = page.getByLabel(/Review and correct extracted text/);
  await correction.waitFor();
  assert.match(await correction.inputValue(), /synthetic/i);
  assert.equal(requests.length, 0);
  await correction.fill('Urgent synthetic message: send your OTP to verify.');
  await button.click();
  await page.getByText('Demo data', { exact: true }).waitFor();
  assert.equal(requests[0].source, 'screenshot');
  assert.equal(requests[0].text, 'Urgent synthetic message: send your OTP to verify.');
  console.log('PASS real CPU OCR -> editable correction -> fixture analyze (Demo data)');

  await page.getByLabel('Image use').selectOption('qr');
  for (const [kind, expected] of [['url', 'https://example.test/qr'], ['text', 'Synthetic plain text']]) {
    const before = requests.length;
    await upload.setInputFiles(`.venv/ingestion-fixtures/synthetic-qr-${kind}.png`);
    const review = page.getByLabel(/Review and correct decoded content/);
    await review.waitFor();
    assert.equal(await review.inputValue(), expected);
    assert.equal(requests.length, before);
    assert.equal(await page.getByRole('link').count(), 0);
    await button.click();
    await page.waitForResponse(response => response.url().endsWith('/api/v1/analyze') && response.ok());
    assert.equal(requests.at(-1).source, 'qr');
    if (kind === 'url') assert.deepEqual(requests.at(-1).urls, [expected]);
    else assert.equal(requests.at(-1).text, expected);
  }
  console.log('PASS real local QR PNG decoding -> text/URL review -> explicit fixture analyze');

  await upload.setInputFiles('.venv/ingestion-fixtures/synthetic-qr-payment.png');
  await page.getByLabel(/Review and correct decoded content/).waitFor();
  assert.equal(await button.isDisabled(), true);
  assert.match(await page.getByRole('alert').innerText(), /no recipient has been verified/);
  await upload.setInputFiles('.venv/ingestion-fixtures/synthetic-no-code.png');
  await page.getByRole('alert').filter({ hasText: 'No readable QR code' }).waitFor();
  assert.equal(await button.count(), 0);
  await upload.setInputFiles('.venv/ingestion-fixtures/synthetic-invalid.png');
  await page.getByRole('alert').filter({ hasText: 'Invalid or damaged' }).waitFor();
  assert.equal(await button.count(), 0);
  assert.equal(external.length, 0);
  await page.screenshot({ path: '.venv/ingestion-browser-smoke.png', fullPage: true });
  console.log('PASS unsupported payment, undecodable/invalid image, stale review cleared; no external requests');
} finally {
  await browser.close();
}
