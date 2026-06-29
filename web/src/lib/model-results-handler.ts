import { getReportStore } from "./node-sqlite-report-store.ts";
import {
  json,
  queryString,
  rejectUnsupportedQuery,
  resolveCampaignFromQuery,
} from "./report-api.ts";

const VALID_OUTPUT_MODES = new Set(["text", "json_schema"]);

export function handleModelResults(req: any, res: any, model: string) {
  const unsupported = rejectUnsupportedQuery(
    req.query,
    new Set([
      "provider",
      "model",
      "benchmark",
      "difficulty",
      "tag",
      "output_mode",
      "campaign",
    ])
  );
  if (unsupported) {
    json(res, 400, { error: `Unsupported query parameter: ${unsupported}` });
    return;
  }

  const outputMode = queryString(req.query.output_mode);
  if (outputMode && !VALID_OUTPUT_MODES.has(outputMode)) {
    json(res, 400, {
      error: `Invalid output_mode: ${outputMode}. Valid values: text, json_schema`,
    });
    return;
  }

  const store = getReportStore();
  const { campaign_id, campaign_metadata } = resolveCampaignFromQuery(store, {
    campaign_id: req.query?.campaign,
    model,
    output_mode: outputMode,
  });
  const result = store.getModelResults(model, {
    benchmark: queryString(req.query.benchmark),
    difficulty: queryString(req.query.difficulty),
    tag: queryString(req.query.tag),
    output_mode: outputMode,
    campaign_id: campaign_id ?? undefined,
  });
  if (!result) {
    json(res, 404, { error: `Model not found: ${model}` });
    return;
  }
  json(res, 200, {
    ...result,
    campaign_id,
    campaign_metadata,
  });
}
