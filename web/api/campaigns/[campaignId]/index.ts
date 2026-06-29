import { getReportStore } from "../../../src/lib/node-sqlite-report-store.ts";
import { json } from "../../../src/lib/report-api.ts";

export default function handler(req: any, res: any) {
  const store = getReportStore();
  const campaignId = String(req.query?.campaignId ?? "");
  if (!campaignId) {
    json(res, 400, { error: "Missing campaignId" });
    return;
  }

  const campaign = store.getCampaign(campaignId);
  if (!campaign) {
    json(res, 404, { error: `Campaign not found: ${campaignId}` });
    return;
  }

  json(res, 200, { campaign });
}
