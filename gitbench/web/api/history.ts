import { getReportStore } from "../src/lib/node-sqlite-report-store.ts";
import { json, rejectUnsupportedQuery, resolveCampaignFromQuery } from "../src/lib/report-api.ts";

export default function handler(req: any, res: any) {
  const unsupported = rejectUnsupportedQuery(req.query, new Set());
  if (unsupported) {
    json(res, 400, { error: `Unsupported query parameter: ${unsupported}` });
    return;
  }
  const store = getReportStore();
  const { campaign_id, campaign_metadata } = resolveCampaignFromQuery(store, {
    campaign_id: req.query?.campaign,
  });
  json(res, 200, {
    runs_meta: store.getHistory(),
    campaign_id,
    campaign_metadata,
  });
}
