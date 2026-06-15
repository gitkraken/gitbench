import { useEffect, useState } from "react";

export function useCampaignId(): string | null {
  const [campaignId, setCampaignId] = useState<string | null>(
    typeof window !== "undefined"
      ? new URLSearchParams(window.location.search).get("campaign")
      : null
  );

  useEffect(() => {
    const handle = () => {
      setCampaignId(
        new URLSearchParams(window.location.search).get("campaign")
      );
    };
    window.addEventListener("popstate", handle);
    return () => window.removeEventListener("popstate", handle);
  }, []);

  return campaignId;
}
