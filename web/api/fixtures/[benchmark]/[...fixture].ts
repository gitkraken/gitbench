import { getReportStore } from "../../../src/lib/node-sqlite-report-store.ts";
import {
  json,
  rejectUnsupportedQuery,
  resolveCampaignFromQuery,
} from "../../../src/lib/report-api.ts";

export default function handler(req: any, res: any) {
  const unsupported = rejectUnsupportedQuery(
    req.query,
    new Set(["benchmark", "fixture", "campaign"]),
  );
  if (unsupported) {
    json(res, 400, { error: `Unsupported query parameter: ${unsupported}` });
    return;
  }

  const store = getReportStore();
  const benchmark = String(req.query.benchmark ?? "");
  const { fixture, attempts } = parseFixturePath(req.query.fixture);
  if (!benchmark || !fixture) {
    json(res, 400, { error: "Missing fixture route parameter" });
    return;
  }

  const { campaign_id, campaign_metadata } = resolveCampaignFromQuery(store, {
    campaign_id: req.query?.campaign,
    benchmark,
  });

  if (attempts) {
    const result = store.getFixtureAttempts(benchmark, fixture, {
      campaign_id: campaign_id ?? undefined,
    });
    if (!result) {
      json(res, 404, { error: `Fixture not found: ${benchmark}/${fixture}` });
      return;
    }
    json(res, 200, {
      fixture: result.fixture,
      campaign_id: result.campaign_id,
      campaign_metadata: campaign_metadata ?? result.campaign_metadata,
      groups: result.groups,
      attempts: result.attempts,
    });
    return;
  }

  const result = store.getFixture(benchmark, fixture, { campaign_id });
  if (!result) {
    json(res, 404, { error: `Fixture not found: ${benchmark}/${fixture}` });
    return;
  }
  json(res, 200, {
    ...result,
    campaign_id,
    campaign_metadata,
  });
}

function parseFixturePath(value: unknown): { fixture: string; attempts: boolean } {
  const parts = Array.isArray(value)
    ? value.map(String)
    : String(value ?? "")
        .split("/")
        .filter(Boolean);
  const attempts = parts.at(-1) === "attempts";
  const fixtureParts = attempts ? parts.slice(0, -1) : parts;
  return {
    fixture: fixtureParts.join("/"),
    attempts,
  };
}
