import type { GitBenchData } from "@/types";

let cachedData: GitBenchData | null = null;

export async function loadData(): Promise<GitBenchData> {
  if (cachedData) {
    return cachedData;
  }

  const response = await fetch("/results.json");
  if (!response.ok) {
    throw new Error(`Failed to load results.json: ${response.status}`);
  }

  cachedData = await response.json();
  return cachedData;
}

export function getCachedData(): GitBenchData | null {
  return cachedData;
}
