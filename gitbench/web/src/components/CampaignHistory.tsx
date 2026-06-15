import { useEffect, useMemo, useState } from "react";
import { loadCampaigns } from "@/lib/report-client";
import type { CampaignListItem } from "@/lib/report-store";
import { Badge } from "@/components/ui/badge";

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString();
}

function statusBadge(campaign: CampaignListItem): string {
  if (campaign.legacy) return "Legacy";
  if (campaign.incomplete) return "Incomplete";
  if (campaign.publishable) return "Published";
  return "Complete";
}

function statusClasses(campaign: CampaignListItem): string {
  if (campaign.legacy)
    return "bg-slate-500/10 text-slate-100 border-slate-500/30";
  if (campaign.incomplete)
    return "bg-amber-500/10 text-amber-100 border-amber-500/30";
  if (campaign.publishable)
    return "bg-emerald-500/10 text-emerald-100 border-emerald-500/30";
  return "bg-(--color-card) text-(--color-text-mid) border-border";
}

export function CampaignHistory() {
  const [campaigns, setCampaigns] = useState<CampaignListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadCampaigns()
      .then((data) => setCampaigns(data.campaigns))
      .catch((err) =>
        setError(err instanceof Error ? err.message : String(err))
      )
      .finally(() => setLoading(false));
  }, []);

  const rows = useMemo(() => {
    const sorted = [...campaigns].sort(
      (a, b) =>
        new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
    );
    return sorted.map((campaign, index) => {
      let delta: number | null = null;
      let compatible = false;
      for (let i = index - 1; i >= 0; i--) {
        const prev = sorted[i];
        if (prev.config_hash && prev.config_hash === campaign.config_hash) {
          compatible = true;
          if (
            prev.mean_success_rate != null &&
            campaign.mean_success_rate != null
          ) {
            delta = campaign.mean_success_rate - prev.mean_success_rate;
          }
          break;
        }
      }
      return { campaign, delta, compatible };
    });
  }, [campaigns]);

  if (loading) {
    return (
      <div className="text-sm text-(--color-text-mid)">
        Loading campaign history…
      </div>
    );
  }
  if (error) {
    return <div className="text-sm text-red-500">History unavailable</div>;
  }
  if (campaigns.length === 0) {
    return (
      <div className="text-sm text-(--color-text-mid)">
        No campaigns on record.
      </div>
    );
  }

  return (
    <div className="card overflow-x-auto p-5">
      <table className="data-table">
        <thead>
          <tr>
            <th>Campaign</th>
            <th>Date</th>
            <th>Status</th>
            <th>Trials</th>
            <th>Mean success</th>
            <th>Valid attempts</th>
            <th>Δ previous compatible</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(({ campaign, delta, compatible }) => {
            const successRate =
              campaign.mean_success_rate != null
                ? `${(campaign.mean_success_rate * 100).toFixed(1)}%`
                : "—";
            const deltaText =
              delta != null
                ? `${delta >= 0 ? "+" : ""}${(delta * 100).toFixed(1)}%`
                : compatible
                ? "—"
                : "incompatible";
            const deltaCls =
              delta == null
                ? "text-(--color-text-dim)"
                : delta > 0
                ? "text-pass"
                : delta < 0
                ? "text-fail"
                : "text-(--color-text-dim)";
            return (
              <tr key={campaign.campaign_id}>
                <td className="font-mono text-xs text-(--color-text-mid)">
                  {campaign.campaign_id}
                </td>
                <td className="font-mono text-[0.68rem] text-(--color-text-dim)">
                  {formatDate(campaign.created_at)}
                </td>
                <td>
                  <Badge
                    variant="outline"
                    className={`font-mono text-[0.65rem] ${statusClasses(
                      campaign
                    )}`}
                  >
                    {statusBadge(campaign)}
                  </Badge>
                </td>
                <td className="font-mono text-[0.68rem] text-(--color-text-dim)">
                  {campaign.completed_trials}/{campaign.planned_trials}
                </td>
                <td className="font-mono text-[0.68rem] text-(--color-text)">
                  {successRate}
                </td>
                <td className="font-mono text-[0.68rem] text-(--color-text-dim)">
                  {campaign.valid_attempts}
                </td>
                <td className={`font-mono text-[0.7rem] ${deltaCls}`}>
                  {deltaText}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
