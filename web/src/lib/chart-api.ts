import { chartData, type ChartKey } from "./chart-data.ts";
import { getReportStore } from "./node-sqlite-report-store.ts";
import {
  json,
  queryString,
  rejectUnsupportedQuery,
  resolveCampaignFromQuery,
} from "./report-api.ts";

export function chartHandler(req: any, res: any, chart: ChartKey): void {
  const unsupported = rejectUnsupportedQuery(
    req.query,
    new Set(["benchmark", "chart", "campaign"])
  );
  if (unsupported) {
    json(res, 400, { error: `Unsupported query parameter: ${unsupported}` });
    return;
  }

  const store = getReportStore();
  const benchmark = queryString(req.query.benchmark);
  const { campaign_id, campaign_metadata } = resolveCampaignFromQuery(store, {
    campaign_id: req.query?.campaign,
    benchmark,
  });
  const summary = store.getSummary({ campaign_id });
  json(res, 200, {
    ...chartData(chart, summary, benchmark),
    campaign_id,
    campaign_metadata,
  });
}
