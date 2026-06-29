import { chartHandler } from "../../src/lib/chart-api.ts";
import { json } from "../../src/lib/report-api.ts";
import type { ChartKey } from "../../src/lib/chart-data.ts";

const SUPPORTED_CHARTS: ReadonlySet<ChartKey> = new Set<ChartKey>([
  "pass-rate",
  "cost",
  "runtime",
  "tokens",
  "quadrant",
  "heatmap",
]);

export default function handler(req: any, res: any) {
  const chart = req.query.chart;
  if (typeof chart !== "string" || !SUPPORTED_CHARTS.has(chart as ChartKey)) {
    json(res, 404, { error: `Unknown chart: ${chart}` });
    return;
  }
  chartHandler(req, res, chart as ChartKey);
}