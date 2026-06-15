import { useEffect, useState } from "react";
import type { CampaignListItem } from "@/lib/report-store";
import { loadCampaigns } from "@/lib/report-client";
import {
  formatCampaignLabel,
  resolveDefaultCampaign,
} from "@/lib/campaign-format";

export { formatCampaignLabel, resolveDefaultCampaign };

export function CampaignSelector() {
  const [campaigns, setCampaigns] = useState<CampaignListItem[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const initialCampaign = params.get("campaign");

    loadCampaigns()
      .then((data) => {
        setCampaigns(data.campaigns);
        const defaultCampaign = resolveDefaultCampaign(
          data.campaigns,
          initialCampaign
        );
        if (defaultCampaign) {
          setSelected(defaultCampaign.campaign_id);
        }
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : String(err));
      })
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!selected) return;
    const params = new URLSearchParams(window.location.search);
    const current = params.get("campaign");
    if (current === selected) return;
    params.set("campaign", selected);
    window.history.replaceState(
      null,
      "",
      `${window.location.pathname}?${params.toString()}`
    );
  }, [selected]);

  if (loading) {
    return (
      <div className="campaign-selector" role="status" aria-live="polite">
        <span className="text-sm text-(--color-text-mid)">
          Loading campaigns…
        </span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="campaign-selector" role="alert">
        <span className="text-sm text-red-500">Campaigns unavailable</span>
      </div>
    );
  }

  if (campaigns.length === 0) {
    return (
      <div className="campaign-selector" role="status">
        <span className="text-sm text-(--color-text-mid)">No campaigns</span>
      </div>
    );
  }

  const activeCampaign = campaigns.find((c) => c.campaign_id === selected);

  return (
    <div className="campaign-selector">
      <label htmlFor="campaign-select" className="sr-only">
        Evaluation campaign
      </label>
      <select
        id="campaign-select"
        value={selected ?? ""}
        onChange={(e) => setSelected(e.target.value)}
        className="rounded-md border border-(--color-border) bg-(--color-surface) px-3 py-1.5 text-sm text-(--color-text) focus:outline-none focus:ring-2 focus:ring-(--color-primary)"
        aria-describedby="campaign-status"
      >
        {campaigns.map((campaign) => (
          <option key={campaign.campaign_id} value={campaign.campaign_id}>
            {formatCampaignLabel(campaign)}
          </option>
        ))}
      </select>
      {activeCampaign && (
        <span
          id="campaign-status"
          className="ml-3 text-xs text-(--color-text-mid)"
        >
          {activeCampaign.incomplete && "Incomplete campaign"}
          {activeCampaign.legacy && "Legacy campaign"}
          {activeCampaign.publishable && "Published"}
        </span>
      )}
    </div>
  );
}
