import { getReportStore } from "../../src/lib/node-sqlite-report-store.ts";
import { json, rejectUnsupportedQuery, resolveCampaignFromQuery } from "../../src/lib/report-api.ts";

export default function handler(req: any, res: any) {
  const unsupported = rejectUnsupportedQuery(
    req.query,
    new Set(["benchmark", "campaign"]),
  );
  if (unsupported) {
    json(res, 400, { error: `Unsupported query parameter: ${unsupported}` });
    return;
  }

  const store = getReportStore();
  const benchmark = String(req.query.benchmark ?? "");
  const { campaign_id, campaign_metadata } = resolveCampaignFromQuery(store, {
    campaign_id: req.query?.campaign,
    benchmark,
  });
  const result = store.getBenchmark(benchmark, { campaign_id });
  if (!result) {
    json(res, 404, { error: `Benchmark not found: ${benchmark}` });
    return;
  }
  json(res, 200, {
    ...result,
    campaign_id,
    campaign_metadata,
  });
}
