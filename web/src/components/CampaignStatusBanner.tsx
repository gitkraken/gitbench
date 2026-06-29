import { useEffect, useState } from "react";
import type { CampaignListItem } from "@/lib/report-store";
import { loadCampaign } from "@/lib/report-client";
import { useCampaignId } from "@/lib/use-campaign";

export function CampaignStatusBanner() {
  const campaignId = useCampaignId();
  const [campaign, setCampaign] = useState<CampaignListItem | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!campaignId) {
      setCampaign(null);
      return;
    }
    setLoading(true);
    loadCampaign(campaignId)
      .then((data) => setCampaign(data.campaign))
      .catch(() => setCampaign(null))
      .finally(() => setLoading(false));
  }, [campaignId]);

  if (loading || !campaign) return null;

  const successRate =
    campaign.mean_success_rate != null
      ? `${(campaign.mean_success_rate * 100).toFixed(1)}%`
      : "—";

  return (
    <div
      className={`rounded-md border px-4 py-2 text-sm ${
        campaign.incomplete
          ? "border-amber-500/30 bg-amber-500/10 text-amber-100"
          : campaign.legacy
          ? "border-slate-500/30 bg-slate-500/10 text-slate-100"
          : "border-emerald-500/30 bg-emerald-500/10 text-emerald-100"
      }`}
      role="status"
      aria-live="polite"
    >
      <span className="font-medium">{campaign.campaign_id}</span>
      {campaign.incomplete && (
        <span className="ml-2">· Incomplete campaign</span>
      )}
      {campaign.legacy && (
        <span className="ml-2">· Legacy one-trial campaign</span>
      )}
      {!campaign.incomplete && !campaign.legacy && (
        <span className="ml-2">· Complete campaign</span>
      )}
      <span className="ml-2">
        · {campaign.completed_trials}/{campaign.planned_trials} trials
      </span>
      <span className="ml-2">· {successRate} mean success</span>
      <span className="ml-2">· {campaign.valid_attempts} valid attempts</span>
    </div>
  );
}
