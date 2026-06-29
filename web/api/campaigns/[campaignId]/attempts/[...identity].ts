import { getReportStore } from "../../../../src/lib/node-sqlite-report-store.ts";
import { json } from "../../../../src/lib/report-api.ts";

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

  const includeOutput = String(req.query?.include_output ?? "false") === "true";
  const allowRawContent =
    campaign.publishable ||
    (campaign.publication_state === "published" && campaign.state === "complete");

  const parts = Array.isArray(req.query?.identity)
    ? req.query.identity
    : [req.query?.identity].filter(Boolean);
  if (parts.length < 4) {
    json(res, 400, {
      error:
        "Identity must include trial_index, model_name, output_mode, and fixture_id",
    });
    return;
  }

  const [trialIndexRaw, modelName, outputMode, fixtureId] = parts;
  const trialIndex = Number(trialIndexRaw);
  if (Number.isNaN(trialIndex)) {
    json(res, 400, { error: "Invalid trial_index" });
    return;
  }

  const attempt = store.getRawAttemptByIdentity(
    campaignId,
    {
      trial_index: trialIndex,
      model_name: modelName,
      output_mode: outputMode,
      fixture_id: fixtureId,
    },
    { includeOutput: includeOutput && allowRawContent },
  );

  if (!attempt) {
    json(res, 404, { error: "Attempt not found" });
    return;
  }

  if (!allowRawContent) {
    delete attempt.model_output;
    delete attempt.parsed_payload;
    delete attempt.raw_structured_output;
    delete attempt.structured_error;
  }

  json(res, 200, { campaign_id: campaignId, attempt });
}
