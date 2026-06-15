import { getReportStore } from "../src/lib/node-sqlite-report-store.ts";
import { json, resolveCampaignFromQuery } from "../src/lib/report-api.ts";

export default function handler(req: any, res: any) {
  const store = getReportStore();
  const summary = store.getSummary();
  const { campaign_id, campaign_metadata } = resolveCampaignFromQuery(
    store,
    {
      campaign_id: req.query?.campaign,
      benchmark: req.query?.benchmark,
      model: req.query?.model,
      output_mode: req.query?.output_mode,
    },
  );
  json(res, 200, {
    ...summary,
    campaign_id,
    campaign_metadata,
  });
}
