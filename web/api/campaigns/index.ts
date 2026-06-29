import { getReportStore } from "../../src/lib/node-sqlite-report-store.ts";
import { json } from "../../src/lib/report-api.ts";

export default function handler(req: any, res: any) {
  const store = getReportStore();
  const filters: Record<string, string> = {};
  if (req.query?.benchmark) filters.benchmark = String(req.query.benchmark);
  if (req.query?.model) filters.model = String(req.query.model);
  if (req.query?.output_mode) filters.output_mode = String(req.query.output_mode);

  const campaigns = store.getCampaigns(
    Object.keys(filters).length > 0 ? filters : undefined,
  );
  json(res, 200, { campaigns });
}
