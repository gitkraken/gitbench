import { getReportStore } from "../../../src/lib/node-sqlite-report-store.ts";
import { json } from "../../../src/lib/report-api.ts";

function parseNumber(value: unknown): number | undefined {
  if (value === undefined || value === null) return undefined;
  const n = Number(value);
  return Number.isNaN(n) ? undefined : n;
}

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

  const options = {
    limit: parseNumber(req.query?.limit) ?? 100,
    offset: parseNumber(req.query?.offset) ?? 0,
    fixture_id: req.query?.fixture_id
      ? String(req.query.fixture_id)
      : undefined,
    includeOutput: includeOutput && allowRawContent,
  };

  const attempts = store.getRawAttempts(campaignId, options);

  // If the campaign is not publishable, strip raw content regardless of
  // include_output. This enforces safety/publication gating for public
  // aggregate queries.
  const sanitizedAttempts = allowRawContent
    ? attempts
    : attempts.map((a) => ({
        ...a,
        model_output: undefined,
        parsed_payload: undefined,
        raw_structured_output: undefined,
        structured_error: undefined,
      }));

  json(res, 200, {
    campaign_id: campaignId,
    publishable: campaign.publishable,
    attempts: sanitizedAttempts,
  });
}
