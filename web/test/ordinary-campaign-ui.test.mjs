import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

function read(path) {
  return readFileSync(path, "utf8");
}

test("ordinary layout and overview do not render campaign controls or empty states", () => {
  const layout = read("src/components/Layout.astro");
  const overview = read("src/pages/index.astro");

  assert.doesNotMatch(layout, /CampaignSelector/);
  assert.doesNotMatch(layout, /No campaigns/);
  assert.doesNotMatch(overview, /CampaignStatusBanner/);
  assert.doesNotMatch(overview, /within a campaign/);
});

test("ordinary evidence and chart copy avoids campaign wording", () => {
  const fixturePage = read("src/pages/fixtures/[benchmark]/[fixture].astro");
  const fixtureEvidence = read("src/components/FixtureCampaignDetail.tsx");
  const passRateChart = read("src/components/charts/PassRateBarChart.tsx");

  assert.match(fixturePage, /Raw Attempt Evidence/);
  assert.doesNotMatch(fixtureEvidence, /No campaign attempts/);
  assert.match(passRateChart, /Latest evaluation/);
});

test("history retains campaign timeline and legacy fallback labels", () => {
  const historyPage = read("src/pages/history.astro");
  const historyComponent = read("src/components/CampaignHistory.tsx");

  assert.match(historyPage, /Evaluation Timeline/);
  assert.match(historyComponent, /campaign_id/);
  assert.match(historyComponent, /No evaluation history records/);
  assert.doesNotMatch(historyComponent, /No campaigns on record/);
});
