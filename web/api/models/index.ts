import { getReportStore } from "../../src/lib/node-sqlite-report-store.ts";
import { json } from "../../src/lib/report-api.ts";

export default function handler(_req: any, res: any) {
  json(res, 200, { models: getReportStore().getModels() });
}
