import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const readPage = (path) => readFileSync(path, "utf8");

const sectionWithLabel = (page, label) => {
  const labelIndex = page.indexOf(`<span>${label}</span>`);
  assert.notEqual(labelIndex, -1, `Missing ${label} label`);

  const sectionStart = page.lastIndexOf("<section", labelIndex);
  const sectionEnd = page.indexOf("</section>", labelIndex);
  assert.notEqual(sectionStart, -1, `Missing ${label} section start`);
  assert.notEqual(sectionEnd, -1, `Missing ${label} section end`);
  return page.slice(sectionStart, sectionEnd + "</section>".length);
};

test("token charts disclose provider-reported source counts and link to methodology", () => {
  const pages = [
    sectionWithLabel(readPage("src/pages/index.astro"), "Token Usage"),
    sectionWithLabel(
      readPage("src/pages/benchmarks/[name].astro"),
      "Benchmark Token Usage",
    ),
  ];

  for (const page of pages) {
    assert.match(page, /Source token counts come from provider-reported usage/);
    assert.match(page, /GitBench\s+calculates the displayed aggregates/);
    assert.match(page, /Provider tokenizers and\s+accounting methods may differ/);
    assert.match(page, /href="\/methodology#token-accounting"/);
    assert.match(page, /Learn more/);
  }
});

test("methodology documents token accounting provenance and comparability", () => {
  const methodology = readPage("src/pages/methodology.astro");

  assert.match(methodology, /<section id="token-accounting">/);
  assert.match(methodology, /usage telemetry returned by\s+provider APIs/);
  assert.match(methodology, /calculates displayed aggregates/);
  assert.match(methodology, /derive a fallback\s+total/);
  assert.match(methodology, /does not\s+independently retokenize/);
  assert.match(methodology, /verify the\s+provider-reported counts/);
  assert.match(methodology, /input, output, cached, and reasoning\s+token categories/);
  assert.match(methodology, /cross-provider token comparisons are not independently normalized/);
});
