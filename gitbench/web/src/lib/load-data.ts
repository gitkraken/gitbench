import type { GitBenchData } from "@/lib/types";
import { loadSummary } from "@/lib/report-client";

let cachedData: GitBenchData | null = null;
let cachedCampaignId: string | null = null;
let pendingData: Promise<GitBenchData> | null = null;

export async function loadData(): Promise<GitBenchData> {
  const campaignId =
    typeof window !== "undefined"
      ? new URLSearchParams(window.location.search).get("campaign")
      : null;
  if (cachedData && cachedCampaignId === campaignId) {
    return cachedData;
  }

  if (pendingData && cachedCampaignId === campaignId) {
    return pendingData;
  }

  pendingData = loadSummary()
    .then((data) => {
      cachedData = data;
      cachedCampaignId = campaignId;
      return data;
    })
    .catch((error) => {
      pendingData = null;
      throw error;
    });

  return pendingData;
}

export function getCachedData(): GitBenchData | null {
  return cachedData;
}
