import { getReportStore } from "../../../../src/lib/node-sqlite-report-store.ts";
import { json, rejectUnsupportedQuery, resolveCampaignFromQuery } from "../../../../src/lib/report-api.ts";

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
  const fixture = String(req.query.fixture ?? "");
  const { campaign_id, campaign_metadata } = resolveCampaignFromQuery(store, {
    campaign_id: req.query?.campaign,
    benchmark,
  });
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
}
