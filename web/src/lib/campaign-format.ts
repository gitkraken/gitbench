import type { CampaignListItem } from "./report-store";

export function formatCampaignLabel(campaign: CampaignListItem): string {
  const date = new Date(campaign.created_at).toLocaleDateString();
  const state = campaign.incomplete ? " (incomplete)" : "";
  const legacy = campaign.legacy ? " (legacy)" : "";
  return `${date} · ${campaign.planned_trials} trials${state}${legacy}`;
}

export function resolveDefaultCampaign(
  campaigns: CampaignListItem[],
  preferredId?: string | null
): CampaignListItem | null {
  if (campaigns.length === 0) return null;

  if (preferredId) {
    const preferred = campaigns.find((c) => c.campaign_id === preferredId);
    if (preferred) return preferred;
  }

  const score = (c: CampaignListItem) =>
    (c.publishable ? 4 : 0) + (!c.incomplete ? 2 : 0) + (!c.legacy ? 1 : 0);

  return campaigns
    .slice()
    .sort(
      (a, b) =>
        score(b) - score(a) ||
        new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
    )[0];
}
