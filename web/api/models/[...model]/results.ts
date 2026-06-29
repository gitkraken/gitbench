import { handleModelResults } from "../../../src/lib/model-results-handler.ts";
import { json, queryString, rejectUnsupportedQuery } from "../../../src/lib/report-api.ts";

export default function handler(req: any, res: any) {
  const unsupported = rejectUnsupportedQuery(req.query, new Set([
    "model",
    "benchmark",
    "difficulty",
    "tag",
    "output_mode",
    "campaign",
  ]));
  if (unsupported) {
    json(res, 400, { error: `Unsupported query parameter: ${unsupported}` });
    return;
  }

  const rawModel = req.query.model;
  const model = Array.isArray(rawModel)
    ? rawModel.map(String).join("/")
    : queryString(rawModel);
  if (!model) {
    json(res, 400, { error: "Missing model route parameter" });
    return;
  }

  handleModelResults(req, res, model);
}
