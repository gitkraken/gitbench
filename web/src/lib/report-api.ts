import type {
  CampaignFilters,
  CampaignListItem,
  ReportStore,
} from "./report-store.ts";

const allowedModelResultFilters = new Set(["benchmark", "difficulty", "tag"]);

export function json(res: any, status: number, body: unknown): void {
  res.status(status).setHeader("content-type", "application/json");
  res.end(JSON.stringify(body));
}

export function rejectUnsupportedQuery(
  query: Record<string, unknown>,
  allowed: Set<string> = allowedModelResultFilters
): string | null {
  for (const key of Object.keys(query)) {
    if (!allowed.has(key)) return key;
  }
  return null;
}

export function queryString(value: unknown): string | undefined {
  if (Array.isArray(value)) return value[0] ? String(value[0]) : undefined;
  return value === undefined ? undefined : String(value);
}

export interface CampaignQuery {
  campaign_id?: string;
  benchmark?: string;
  model?: string;
  output_mode?: string;
}

export function resolveCampaignFromQuery(
  store: ReportStore,
  query: CampaignQuery
): { campaign_id: string | null; campaign_metadata: CampaignListItem | null } {
  const filters = {
    benchmark: query.benchmark,
    model: query.model,
    output_mode: query.output_mode,
  };
  if (query.campaign_id) {
    const compatible = store.checkCampaignCompatibility(
      query.campaign_id,
      filters
    );
    return {
      campaign_id: compatible ? query.campaign_id : null,
      campaign_metadata: compatible
        ? store
            .getCampaigns(filters)
            .find((c) => c.campaign_id === query.campaign_id) ?? null
        : null,
    };
  }
  const defaultCampaign = store.getDefaultCampaign(filters);
  return {
    campaign_id: defaultCampaign?.campaign_id ?? null,
    campaign_metadata: defaultCampaign ?? null,
  };
}
