import { mkdir, writeFile, appendFile } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { chromium } from 'playwright';
import monitorConfig from '../playwright.production.config.mjs';

export const PRODUCTION_URL = monitorConfig.targetUrl;
export const MEASUREMENT_ID = monitorConfig.measurementId;
export const OBSERVATION_TIMEOUT_MS = monitorConfig.observationTimeoutMs;

function parsedUrl(value) {
  try {
    return new URL(value);
  } catch {
    return null;
  }
}

function requestField(request, field) {
  const value = request[field];
  return typeof value === 'function' ? value.call(request) : value;
}

function hostnameIsAllowed(hostname, additionalHosts = []) {
  return hostname === 'google-analytics.com'
    || hostname.endsWith('.google-analytics.com')
    || additionalHosts.includes(hostname);
}

export function isCollectionDestination(value, additionalHosts = []) {
  const url = parsedUrl(value);
  if (!url || url.pathname !== '/g/collect') return false;
  if (!hostnameIsAllowed(url.hostname, additionalHosts)) return false;
  return url.protocol === 'https:' || additionalHosts.includes(url.hostname);
}

export function parseCollectionEvents(request) {
  const url = parsedUrl(requestField(request, 'url'));
  if (!url) return [];

  const sharedParameters = new URLSearchParams(url.searchParams);
  const method = requestField(request, 'method')?.toUpperCase();
  const body = method === 'POST' ? requestField(request, 'postData') ?? '' : '';
  const eventLines = body.split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
  const lines = eventLines.length > 0 ? eventLines : [''];

  return lines.map((line) => {
    const parameters = new URLSearchParams(sharedParameters);
    for (const [key, value] of new URLSearchParams(line)) parameters.set(key, value);
    return {
      measurementId: parameters.get('tid') ?? null,
      eventName: parameters.get('en') ?? null,
      pageLocation: parameters.get('dl') ?? null,
    };
  });
}

function normalizedPageLocation(value) {
  const url = parsedUrl(value);
  if (!url) return null;
  return `${url.origin}${url.pathname}`;
}

export function matchesExpectedPageView(request, {
  measurementId = MEASUREMENT_ID,
  expectedPageLocation = PRODUCTION_URL,
  additionalCollectionHosts = [],
} = {}) {
  if (!isCollectionDestination(requestField(request, 'url'), additionalCollectionHosts)) return false;
  const expectedLocation = normalizedPageLocation(expectedPageLocation);
  return parseCollectionEvents(request).some((event) => (
    event.measurementId === measurementId
    && event.eventName === 'page_view'
    && normalizedPageLocation(event.pageLocation) === expectedLocation
  ));
}

function safeUrl(value) {
  const url = parsedUrl(value);
  return url ? `${url.origin}${url.pathname}` : 'unparseable URL';
}

function isTagScript(value) {
  const url = parsedUrl(value);
  return url?.pathname === '/gtag/js';
}

function safePageLocation(value) {
  return normalizedPageLocation(value);
}

function summarizeEvents(request) {
  return parseCollectionEvents(request).map((event) => ({
    measurementId: event.measurementId,
    eventName: event.eventName,
    pageLocation: safePageLocation(event.pageLocation),
  }));
}

function createAttemptRecord(attempt, pageUrl) {
  return {
    attempt,
    pageUrl: safeUrl(pageUrl),
    passed: false,
    failure: null,
    durationMs: 0,
    navigation: { status: null, successful: false, error: null },
    tag: { requested: false, loaded: false, status: null, error: null },
    pageErrors: [],
    networkFailures: [],
    observedCollections: [],
  };
}

export async function runAttempt(browser, {
  attempt = 1,
  pageUrl = PRODUCTION_URL,
  measurementId = MEASUREMENT_ID,
  expectedPageLocation = PRODUCTION_URL,
  timeoutMs = OBSERVATION_TIMEOUT_MS,
  additionalCollectionHosts = [],
} = {}) {
  const record = createAttemptRecord(attempt, pageUrl);
  const startedAt = Date.now();
  const deadlineAt = startedAt + timeoutMs;
  let timer;
  let resolveMatched;
  const matched = new Promise((resolve) => { resolveMatched = resolve; });
  const deadline = new Promise((resolve) => {
    timer = setTimeout(() => resolve(false), Math.max(1, deadlineAt - Date.now()));
  });
  let matchedAlready = false;
  let context;

  try {
    context = await browser.newContext({ serviceWorkers: monitorConfig.browser.serviceWorkers });
    const page = await context.newPage();

    page.on('pageerror', (error) => {
      if (record.pageErrors.length < 20) record.pageErrors.push(error.message);
    });
    page.on('request', (request) => {
      if (isTagScript(request.url())) record.tag.requested = true;
    });
    page.on('response', (response) => {
      if (isTagScript(response.url())) {
        record.tag.status = response.status();
        record.tag.loaded = response.ok();
      }
    });
    page.on('requestfailed', (request) => {
      const url = request.url();
      const relevant = request.resourceType() === 'document'
        || request.resourceType() === 'script'
        || isTagScript(url);
      if (!relevant || record.networkFailures.length >= 30) return;
      record.networkFailures.push({
        url: safeUrl(url),
        resourceType: request.resourceType(),
        error: request.failure()?.errorText ?? 'request failed',
      });
      if (isTagScript(url)) record.tag.error = request.failure()?.errorText ?? 'request failed';
    });

    await context.route('**/*', async (route) => {
      const request = route.request();
      if (!isCollectionDestination(request.url(), additionalCollectionHosts)) {
        await route.continue();
        return;
      }

      const events = summarizeEvents(request);
      if (record.observedCollections.length < 30) {
        record.observedCollections.push({
          destination: safeUrl(request.url()),
          method: request.method(),
          events,
        });
      }
      const isMatch = !matchedAlready && matchesExpectedPageView(request, {
        measurementId,
        expectedPageLocation,
        additionalCollectionHosts,
      });

      await route.fulfill({ status: 204, body: '' });
      if (isMatch) {
        matchedAlready = true;
        resolveMatched(true);
      }
    });

    const navigationTimeout = Math.max(1, deadlineAt - Date.now());
    try {
      const response = await page.goto(pageUrl, {
        waitUntil: 'domcontentloaded',
        timeout: navigationTimeout,
      });
      record.navigation.status = response?.status() ?? null;
      record.navigation.successful = response?.ok() ?? false;
      if (!record.navigation.successful) {
        record.failure = response
          ? `Main document returned HTTP ${response.status()}.`
          : 'Navigation did not return a main-document response.';
      }
    } catch (error) {
      record.navigation.error = error.message;
      record.failure = 'Production page navigation failed.';
    }

    if (!record.failure) {
      const observed = await Promise.race([matched, deadline]);
      if (observed) {
        record.passed = true;
      } else {
        record.failure = `No matching page_view collection request was observed within ${timeoutMs} ms.`;
      }
    }
  } catch (error) {
    record.failure ??= `Monitor setup failed: ${error.message}`;
  } finally {
    clearTimeout(timer);
    record.durationMs = Date.now() - startedAt;
    await context?.close().catch((error) => {
      record.failure ??= `Browser context could not be closed: ${error.message}`;
      record.passed = false;
    });
  }

  return record;
}

export function formatRunSummary(result) {
  const lines = [
    `Production analytics event-generation check: **${result.passed ? 'PASS' : 'FAIL'}**`,
    `Target: \`${PRODUCTION_URL}\``,
    `Measurement ID: \`${MEASUREMENT_ID}\``,
  ];
  for (const attempt of result.attempts) {
    const status = attempt.passed ? 'passed' : `failed: ${attempt.failure}`;
    lines.push(`- Attempt ${attempt.attempt}: ${status} (${attempt.durationMs} ms); ${attempt.observedCollections.length} collection request(s) observed and suppressed.`);
  }
  if (result.attempts.length > 1) {
    lines.push(result.passed
      ? 'The retry recovered; diagnostics for the failed attempt are retained.'
      : 'Both attempts failed; review the diagnostic artifact.');
  }
  lines.push(`Retry outcome: **${result.retryOutcome}**.`);
  lines.push('This check verifies event generation. It does not verify Google receipt or GA report ingestion.');
  return `${lines.join('\n')}\n`;
}

async function storeDiagnostics(result, directory) {
  await mkdir(directory, { recursive: true });
  for (const attempt of result.attempts.filter((entry) => !entry.passed)) {
    await writeFile(
      path.join(directory, `attempt-${attempt.attempt}.json`),
      `${JSON.stringify(attempt, null, 2)}\n`,
      'utf8',
    );
  }
}

export async function runMonitor({
  browser,
  pageUrl = PRODUCTION_URL,
  measurementId = MEASUREMENT_ID,
  expectedPageLocation = PRODUCTION_URL,
  timeoutMs = OBSERVATION_TIMEOUT_MS,
  additionalCollectionHosts = [],
  diagnosticsDirectory = path.join(process.env.RUNNER_TEMP || os.tmpdir(), 'production-analytics-diagnostics'),
  attemptRunner = runAttempt,
} = {}) {
  const attempts = [];
  for (let attempt = 1; attempt <= monitorConfig.maxAttempts; attempt += 1) {
    const record = await attemptRunner(browser, {
      attempt,
      pageUrl,
      measurementId,
      expectedPageLocation,
      timeoutMs,
      additionalCollectionHosts,
    });
    attempts.push(record);
    if (record.passed) break;
  }

  const result = {
    passed: attempts.some((attempt) => attempt.passed),
    attempts,
  };
  result.retryOutcome = attempts.length === 1
    ? 'not-needed'
    : result.passed ? 'recovered' : 'failed-after-retry';
  for (const attempt of attempts) attempt.retryOutcome = result.retryOutcome;
  await storeDiagnostics(result, diagnosticsDirectory);
  const summary = formatRunSummary(result);
  const summaryFile = process.env.GITHUB_STEP_SUMMARY;
  if (summaryFile) await appendFile(summaryFile, `${summary}\n`, 'utf8');
  return result;
}

async function main() {
  let browser;
  try {
    browser = await chromium.launch({ headless: monitorConfig.browser.headless });
    const result = await runMonitor({ browser });
    process.stdout.write(formatRunSummary(result));
    if (!result.passed) process.exitCode = 1;
  } catch (error) {
    const summary = `Production analytics event-generation check: **FAIL**\n\nMonitor could not start: ${error.message}\n`;
    process.stderr.write(`${summary}\n`);
    if (process.env.GITHUB_STEP_SUMMARY) {
      await appendFile(process.env.GITHUB_STEP_SUMMARY, `${summary}\n`, 'utf8');
    }
    process.exitCode = 1;
  } finally {
    await browser?.close();
  }
}

if (process.argv[1] && import.meta.url === new URL(`file://${process.argv[1]}`).href) {
  await main();
}
