import assert from "node:assert/strict";
import test from "node:test";

import {
  formatCampaignLabel,
  resolveDefaultCampaign,
} from "../src/lib/campaign-format.ts";

function campaign(overrides = {}) {
  return {
    campaign_id: "cmp-default",
    created_at: "2026-06-01T00:00:00Z",
    state: "complete",
    publication_state: "published",
    legacy: false,
    planned_trials: 3,
    completed_trials: 3,
    valid_attempts: 6,
    passing_attempts: 4,
    excluded_attempts: 0,
    mean_success_rate: 0.75,
    compatible: true,
    incomplete: false,
    publishable: true,
    ...overrides,
  };
}

test("formatCampaignLabel includes date, trial count, and status", () => {
  const label = formatCampaignLabel(
    campaign({
      created_at: "2026-06-10T12:00:00Z",
      planned_trials: 5,
    }),
  );
  assert.match(label, /6\/10\/2026/);
  assert.match(label, /5 trials/);
});

test("formatCampaignLabel marks incomplete campaigns", () => {
  const label = formatCampaignLabel(campaign({ incomplete: true, publishable: false }));
  assert.match(label, /\(incomplete\)/);
});

test("formatCampaignLabel marks legacy campaigns", () => {
  const label = formatCampaignLabel(campaign({ legacy: true, publishable: false }));
  assert.match(label, /\(legacy\)/);
});

test("resolveDefaultCampaign prefers an explicit preferred ID", () => {
  const a = campaign({ campaign_id: "a", publishable: true });
  const b = campaign({ campaign_id: "b", publishable: false });
  assert.equal(resolveDefaultCampaign([a, b], "b")?.campaign_id, "b");
});

test("resolveDefaultCampaign prefers publishable complete non-legacy campaigns", () => {
  const publishable = campaign({
    campaign_id: "publishable",
    publishable: true,
    incomplete: false,
    legacy: false,
  });
  const incomplete = campaign({
    campaign_id: "incomplete",
    publishable: false,
    incomplete: true,
    legacy: false,
  });
  const legacy = campaign({
    campaign_id: "legacy",
    publishable: false,
    incomplete: false,
    legacy: true,
  });
  const chosen = resolveDefaultCampaign([incomplete, legacy, publishable]);
  assert.equal(chosen?.campaign_id, "publishable");
});

test("resolveDefaultCampaign falls back to the latest campaign when none are publishable", () => {
  const older = campaign({
    campaign_id: "older",
    publishable: false,
    created_at: "2026-06-01T00:00:00Z",
  });
  const newer = campaign({
    campaign_id: "newer",
    publishable: false,
    created_at: "2026-06-05T00:00:00Z",
  });
  assert.equal(resolveDefaultCampaign([older, newer])?.campaign_id, "newer");
});

test("resolveDefaultCampaign returns null for an empty list", () => {
  assert.equal(resolveDefaultCampaign([]), null);
});

test("resolveDefaultCampaign ignores unknown preferred IDs", () => {
  const c = campaign({ campaign_id: "known" });
  assert.equal(resolveDefaultCampaign([c], "missing")?.campaign_id, "known");
});
