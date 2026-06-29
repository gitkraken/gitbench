import { useEffect, useMemo, useState } from "react";
import { loadModelResults } from "@/lib/report-client";
import type { FixtureResult } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { useCampaignId } from "@/lib/use-campaign";
import {
  resolveReportViewState,
  type ReportOutputMode,
} from "@/lib/report-url-state";

interface ReliabilityCounts {
  stablePass: number;
  flaky: number;
  stableFail: number;
  totalFixtures: number;
  validAttempts: number;
  passingAttempts: number;
  meanSuccessRate: number | null;
}

function classifyFixture(
  results: FixtureResult[]
): "stable_pass" | "flaky" | "stable_fail" | "unknown" {
  const valid = results.filter((r) => r.error == null);
  if (valid.length === 0) return "unknown";
  const passed = valid.filter((r) => r.passed).length;
  if (passed === valid.length) return "stable_pass";
  if (passed === 0) return "stable_fail";
  return "flaky";
}

export interface ModelReliabilitySummaryProps {
  model: string;
  outputMode?: string;
  reportGroupId?: string;
  availableOutputModes?: string[];
}

function isOutputMode(value: string): value is ReportOutputMode {
  return value === "text" || value === "json_schema" || value === "both";
}

function readInitialOutputMode(
  fallback: string,
  reportGroupId: string,
  availableOutputModes: string[]
): string {
  if (typeof window === "undefined") return fallback;
  const defaultOutputMode = isOutputMode(fallback) ? fallback : "text";
  return resolveReportViewState(
    window.location.search,
    [{ id: reportGroupId }],
    {
      defaultSelectedGroups: [reportGroupId],
      defaultOutputMode,
      availableOutputModes,
    }
  ).outputMode;
}

function fetchOutputMode(mode: string): string {
  // In "both" mode, fetch text results (comparison section covers cross-mode deltas)
  if (mode === "both") return "text";
  return mode;
}

export function ModelReliabilitySummary({
  model,
  outputMode = "text",
  reportGroupId = "current",
  availableOutputModes = [outputMode],
}: ModelReliabilitySummaryProps) {
  // Read initial output mode from URL state, falling back to the page default.
  const [activeOutputMode, setActiveOutputMode] = useState<string>(() =>
    readInitialOutputMode(outputMode, reportGroupId, availableOutputModes)
  );

  const [results, setResults] = useState<Record<
    string,
    FixtureResult[]
  > | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const campaignId = useCampaignId();

  // Listen for output-mode-change events from the vanilla JS toggle
  useEffect(() => {
    function handleOutputModeChange(e: Event) {
      const detail = (e as CustomEvent).detail;
      if (detail && typeof detail.mode === "string") {
        setActiveOutputMode(detail.mode);
      }
    }
    window.addEventListener("output-mode-change", handleOutputModeChange);
    return () =>
      window.removeEventListener("output-mode-change", handleOutputModeChange);
  }, []);

  // Use "text" for fetch in "both" mode (comparison section covers cross-mode)
  const fetchMode = fetchOutputMode(activeOutputMode);

  useEffect(() => {
    setLoading(true);
    setError(null);
    loadModelResults(model, { output_mode: fetchMode })
      .then((data) => {
        setResults(data.results ?? {});
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : String(err));
      })
      .finally(() => setLoading(false));
  }, [model, fetchMode, campaignId]);

  const byBenchmark = useMemo(() => {
    if (!results) return {};
    const summary: Record<string, ReliabilityCounts> = {};
    let totalValid = 0;
    let totalPassing = 0;

    for (const [benchmark, fixtures] of Object.entries(results)) {
      const byFixture: Record<string, FixtureResult[]> = {};
      for (const r of fixtures) {
        byFixture[r.fixture_id] = byFixture[r.fixture_id] ?? [];
        byFixture[r.fixture_id].push(r);
      }
      const counts: ReliabilityCounts = {
        stablePass: 0,
        flaky: 0,
        stableFail: 0,
        totalFixtures: 0,
        validAttempts: 0,
        passingAttempts: 0,
        meanSuccessRate: null,
      };
      for (const fixtureResults of Object.values(byFixture)) {
        const classification = classifyFixture(fixtureResults);
        if (classification === "stable_pass") counts.stablePass++;
        else if (classification === "flaky") counts.flaky++;
        else if (classification === "stable_fail") counts.stableFail++;
        counts.totalFixtures++;
        const valid = fixtureResults.filter((r) => r.error == null);
        counts.validAttempts += valid.length;
        counts.passingAttempts += valid.filter((r) => r.passed).length;
      }
      totalValid += counts.validAttempts;
      totalPassing += counts.passingAttempts;
      counts.meanSuccessRate =
        counts.validAttempts > 0
          ? counts.passingAttempts / counts.validAttempts
          : null;
      summary[benchmark] = counts;
    }
    return summary;
  }, [results]);

  if (loading) {
    return (
      <div className="text-sm text-(--color-text-mid)">
        Loading reliability summary…
      </div>
    );
  }
  if (error) {
    return (
      <div className="text-sm text-red-500">
        Reliability summary unavailable
      </div>
    );
  }

  const benchmarks = Object.keys(byBenchmark).sort();
  if (benchmarks.length === 0) {
    return (
      <div className="text-sm text-(--color-text-mid)">
        No repeated-trial data available for this model and output mode.
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left font-mono text-[0.7rem]">
        <thead>
          <tr className="text-(--color-text-dim) border-b border-border">
            <th className="pb-2 pr-3 font-normal">Benchmark</th>
            <th className="pb-2 pr-3 font-normal text-right">Stable pass</th>
            <th className="pb-2 pr-3 font-normal text-right">Flaky</th>
            <th className="pb-2 pr-3 font-normal text-right">Stable fail</th>
            <th className="pb-2 pr-3 font-normal text-right">Mean success</th>
            <th className="pb-2 font-normal text-right">Fixtures</th>
          </tr>
        </thead>
        <tbody>
          {benchmarks.map((benchmark) => {
            const counts = byBenchmark[benchmark];
            const rate =
              counts.meanSuccessRate != null
                ? `${(counts.meanSuccessRate * 100).toFixed(1)}%`
                : "—";
            return (
              <tr
                key={benchmark}
                className="border-b border-(--color-border-dim)"
              >
                <td className="py-2 pr-3 text-(--color-text-mid)">
                  {benchmark}
                </td>
                <td className="py-2 pr-3 text-right text-pass">
                  {counts.stablePass}
                </td>
                <td className="py-2 pr-3 text-right text-(--color-warn)">
                  {counts.flaky}
                </td>
                <td className="py-2 pr-3 text-right text-fail">
                  {counts.stableFail}
                </td>
                <td className="py-2 pr-3 text-right text-(--color-text)">
                  {rate}
                </td>
                <td className="py-2 text-right text-(--color-text-dim)">
                  {counts.totalFixtures}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
