import assert from 'node:assert/strict';
import { createServer } from 'node:http';
import { mkdtemp, readFile, rm } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { after, before, test } from 'node:test';
import { chromium } from 'playwright';
import {
  isCollectionDestination,
  matchesExpectedPageView,
  parseCollectionEvents,
  runAttempt,
  runMonitor,
} from '../scripts/production-analytics-monitor.mjs';

const MEASUREMENT_ID = 'G-5SDMWDGT2G';
let browser;
let server;
let origin;
let scenarioQueue = [];
let fallbackScenario = 'healthy';
let collectorRequestCount = 0;
let fixtureDiagnosticsDirectory;

function siteStartup(scenario) {
  switch (scenario) {
    case 'missing':
      return '<script>window.dataLayer = [];</script>';
    case 'arrays':
      return `<script>
        window.dataLayer = window.dataLayer || [];
        function gtag() { window.dataLayer.push(Array.from(arguments)); }
        gtag('js', new Date());
        gtag('config', '${MEASUREMENT_ID}');
      </script>`;
    case 'strings':
      return `<script>
        window.dataLayer = window.dataLayer || [];
        window.dataLayer.push("gtag('config', '${MEASUREMENT_ID}')");
      </script>`;
    case 'syntax-error':
      return '<script>const invalid = ;</script>';
    case 'reference-error':
      return "<script>throw new ReferenceError('fixture reference error')</script>";
    default:
      return `<script>
        window.dataLayer = window.dataLayer || [];
        function gtag() { window.dataLayer.push(arguments); }
        gtag('js', new Date());
        gtag('config', '${MEASUREMENT_ID}');
      </script>`;
  }
}

function fixturePage(scenario) {
  return `<!doctype html>
    <html><head><title>Analytics fixture</title>
    <script async src="/gtag/js?id=${MEASUREMENT_ID}"></script>
    ${siteStartup(scenario)}
    <script>window.__fixtureScenario = ${JSON.stringify(scenario)};</script>
    </head><body><main>Fixture</main></body></html>`;
}

const fixtureTag = `
  const inspectQueue = () => {
    if (document.readyState === 'loading') return setTimeout(inspectQueue, 0);
    const validCommand = (entry) => Object.prototype.toString.call(entry) === '[object Arguments]';
    const queue = window.dataLayer || [];
    const hasStartup = queue.some((entry) => validCommand(entry) && entry[0] === 'js');
    const config = queue.find((entry) => validCommand(entry) && entry[0] === 'config');
    if (!hasStartup || !config) return;

    const scenario = window.__fixtureScenario;
    const measurementId = scenario === 'wrong-measurement' ? 'G-OTHER' : config[1];
    const eventName = scenario === 'wrong-event' ? 'scroll' : 'page_view';
    const pageLocation = location.origin + '/';
    const makeHit = (name) => {
      const params = new URLSearchParams({ tid: measurementId, en: name, dl: pageLocation });
      params.set('cid', 'fixture-client-id');
      params.set('sid', 'fixture-session-id');
      return fetch('/g/collect?' + params.toString());
    };
    void Promise.all([makeHit(eventName), makeHit('user_engagement')]);
  };
  inspectQueue();
`;

async function setScenarios(scenarios) {
  scenarioQueue = [...scenarios];
  fallbackScenario = scenarios.at(-1) ?? 'healthy';
}

async function runFixture({ scenarios = ['healthy'], timeoutMs = 800, diagnosticsDirectory } = {}) {
  await setScenarios(scenarios);
  return runMonitor({
    browser,
    pageUrl: `${origin}/`,
    expectedPageLocation: `${origin}/`,
    additionalCollectionHosts: [new URL(origin).hostname],
    timeoutMs,
    diagnosticsDirectory: diagnosticsDirectory ?? fixtureDiagnosticsDirectory,
  });
}

before(async () => {
  browser = await chromium.launch({ headless: true });
  fixtureDiagnosticsDirectory = await mkdtemp(path.join(os.tmpdir(), 'analytics-monitor-fixtures-'));
  server = createServer((request, response) => {
    const requestPath = new URL(request.url ?? '/', 'http://127.0.0.1').pathname;
    if (requestPath === '/gtag/js') {
      response.writeHead(200, { 'content-type': 'text/javascript' });
      response.end(fixtureTag);
      return;
    }
    if (requestPath === '/g/collect') {
      collectorRequestCount += 1;
      response.writeHead(204);
      response.end();
      return;
    }
    if (requestPath !== '/') {
      response.writeHead(404);
      response.end();
      return;
    }
    const scenario = scenarioQueue.shift() ?? fallbackScenario;
    response.writeHead(200, { 'content-type': 'text/html' });
    response.end(fixturePage(scenario));
  });
  await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
  const address = server.address();
  origin = `http://127.0.0.1:${address.port}`;
});

after(async () => {
  await browser?.close();
  await new Promise((resolve, reject) => server?.close((error) => error ? reject(error) : resolve()));
  if (fixtureDiagnosticsDirectory) await rm(fixtureDiagnosticsDirectory, { recursive: true, force: true });
});

test('recognizes Google collection hosts without accepting suffix lookalikes', () => {
  assert.equal(isCollectionDestination('https://google-analytics.com/g/collect'), true);
  assert.equal(isCollectionDestination('https://region1.google-analytics.com/g/collect'), true);
  assert.equal(isCollectionDestination('https://notgoogle-analytics.com/g/collect'), false);
  assert.equal(isCollectionDestination('https://google-analytics.com.evil.test/g/collect'), false);
  assert.equal(isCollectionDestination('https://google-analytics.com/collect'), false);
});

test('parses GET, URL-encoded POST, and batched POST events with shared parameters', () => {
  const expectedPageLocation = 'https://gitbench.gitkraken.com/';
  const getRequest = {
    url: `https://region1.google-analytics.com/g/collect?tid=${MEASUREMENT_ID}&en=page_view&dl=${encodeURIComponent(expectedPageLocation)}`,
    method: 'GET',
  };
  assert.equal(matchesExpectedPageView(getRequest), true);

  const postRequest = {
    url: `https://www.google-analytics.com/g/collect?v=2&tid=${MEASUREMENT_ID}`,
    method: 'POST',
    postData: `en=session_start&dl=${encodeURIComponent(expectedPageLocation)}\nen=page_view&dl=${encodeURIComponent(expectedPageLocation)}`,
  };
  assert.deepEqual(parseCollectionEvents(postRequest).map((event) => event.eventName), ['session_start', 'page_view']);
  assert.equal(matchesExpectedPageView(postRequest), true);
  assert.equal(matchesExpectedPageView({ ...getRequest, url: getRequest.url.replace('region1.google-analytics.com', 'example.test') }), false);
});

test('healthy startup emits a matching page view and suppresses page-view and engagement requests', async () => {
  collectorRequestCount = 0;
  const result = await runFixture();
  assert.equal(result.passed, true, JSON.stringify(result, null, 2));
  assert.equal(result.attempts.length, 1);
  assert.equal(result.attempts[0].navigation.successful, true);
  assert.equal(result.attempts[0].tag.loaded, true);
  const events = result.attempts[0].observedCollections.flatMap((request) => request.events.map((event) => event.eventName));
  assert.ok(events.includes('page_view'));
  assert.ok(events.includes('user_engagement'));
  assert.equal(collectorRequestCount, 0, 'the instrumented collector must receive no intercepted collection traffic');
});

test('missing startup, argument arrays, string commands, syntax errors, reference errors, wrong IDs, and wrong events fail', async () => {
  const scenarios = [
    ['missing', /within/],
    ['arrays', /within/],
    ['strings', /within/],
    ['syntax-error', /within/],
    ['reference-error', /within/],
    ['wrong-measurement', /within/],
    ['wrong-event', /within/],
  ];
  for (const [scenario, failurePattern] of scenarios) {
    const result = await runFixture({ scenarios: [scenario], timeoutMs: 250 });
    assert.equal(result.passed, false, `${scenario} should fail`);
    assert.match(result.attempts[0].failure, failurePattern);
    if (scenario === 'syntax-error' || scenario === 'reference-error') {
      assert.ok(result.attempts[0].pageErrors.length > 0, `${scenario} should be captured as a page error`);
    }
    if (scenario === 'wrong-event') {
      const diagnostics = await readFile(path.join(fixtureDiagnosticsDirectory, 'attempt-1.json'), 'utf8');
      assert.equal(diagnostics.includes('fixture-client-id'), false);
      assert.equal(diagnostics.includes('fixture-session-id'), false);
    }
  }
});

test('persistent failures retain both attempts and a first-attempt failure followed by recovery passes', async () => {
  const diagnosticsDirectory = await mkdtemp(path.join(os.tmpdir(), 'analytics-monitor-test-'));
  try {
    const persistent = await runFixture({
      scenarios: ['missing', 'missing'],
      timeoutMs: 200,
      diagnosticsDirectory,
    });
    assert.equal(persistent.passed, false);
    assert.equal(persistent.attempts.length, 2);
    assert.ok((await readFile(path.join(diagnosticsDirectory, 'attempt-1.json'), 'utf8')).includes('No matching page_view'));
    assert.ok((await readFile(path.join(diagnosticsDirectory, 'attempt-2.json'), 'utf8')).includes('No matching page_view'));

    const recoveryDirectory = await mkdtemp(path.join(os.tmpdir(), 'analytics-monitor-recovery-'));
    try {
      const recovered = await runFixture({
        scenarios: ['missing', 'healthy'],
        timeoutMs: 250,
        diagnosticsDirectory: recoveryDirectory,
      });
      assert.equal(recovered.passed, true, JSON.stringify(recovered, null, 2));
      assert.deepEqual(recovered.attempts.map((attempt) => attempt.passed), [false, true]);
      assert.ok((await readFile(path.join(recoveryDirectory, 'attempt-1.json'), 'utf8')).includes('"attempt": 1'));
    } finally {
      await rm(recoveryDirectory, { recursive: true, force: true });
    }
  } finally {
    await rm(diagnosticsDirectory, { recursive: true, force: true });
  }
});
