import { useState, useEffect, useMemo } from "react";
import type { GitBenchData } from "@/lib/types";
import { loadHeatmapChart, type HeatmapChartData } from "@/lib/report-client";
import { modelPath } from "@/lib/routes";
import ModelOutputControls from "@/components/charts/ModelOutputControls";
import { Badge } from "@/components/ui/badge";
import { useSyncedModelSelection } from "@/components/charts/useSyncedModelSelection";

function classifyReliability(passAtK: number): {
  label: string;
  title: string;
} {
  if (passAtK >= 1) return { label: "stable pass", title: "Stable pass" };
  if (passAtK <= 0) return { label: "stable fail", title: "Stable fail" };
  return { label: "flaky", title: "Flaky" };
}

function heatBg(ratio: number): string {
  if (ratio >= 0.9) return "rgba(16,185,129,0.28)";
  if (ratio >= 0.8) return "rgba(16,185,129,0.18)";
  if (ratio >= 0.5) return "rgba(245,158,11,0.18)";
  if (ratio > 0) return "rgba(245,158,11,0.12)";
  return "rgba(244,63,94,0.15)";
}

function heatColor(ratio: number): string {
  if (ratio >= 0.8) return "var(--color-pass)";
  if (ratio > 0) return "var(--color-warn)";
  return "var(--color-fail)";
}

import { useCampaignId } from "@/lib/use-campaign";

export default function BenchmarkHeatmap() {
  const [data, setData] = useState<HeatmapChartData | null>(null);
  const campaignId = useCampaignId();
  const selectionData = useMemo<GitBenchData | null>(() => {
    if (!data) return null;
    return {
      models: data.models,
      benchmarks: data.benchmarks,
      model_summaries: {},
      model_runtimes: {},
      model_token_summaries: {},
      matrix: {},
      fixtures: {},
      fixture_index: {},
      runs_meta: [],
      base_model_groups: data.base_model_groups,
    };
  }, [data]);
  const {
    selectedGroups,
    setSelectedGroups,
    selectedModels,
    outputMode,
    setOutputMode,
    availableOutputModes,
  } = useSyncedModelSelection(selectionData);

  useEffect(() => {
    loadHeatmapChart().then((d) => {
      setData(d);
    });
  }, [campaignId]);

  if (!data || !selectionData) return <div>Loading...</div>;

  return (
    <div>
      <ModelOutputControls
        data={selectionData}
        selectedGroups={selectedGroups}
        onSelectedGroupsChange={setSelectedGroups}
        outputMode={outputMode}
        onOutputModeChange={setOutputMode}
        availableOutputModes={availableOutputModes}
      />
      <div className="card overflow-x-auto p-5">
        <table className="data-table">
          <thead>
            <tr>
              <th>Benchmark</th>
              {selectedModels.map((m) => (
                <th key={m}>
                  <a href={modelPath(m)} className="text-inherit no-underline">
                    {m}
                  </a>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.benchmarks.map((bench, benchIndex) => (
              <tr key={bench}>
                <td className="font-mono text-xs text-(--color-text-mid)">
                  <a
                    href={`/benchmarks/${bench}`}
                    className="text-inherit no-underline"
                  >
                    {bench}
                  </a>
                </td>
                {selectedModels.map((m) => {
                  const cell = data.matrix[m]?.[benchIndex];
                  if (!cell) {
                    return (
                      <td
                        key={m}
                        title={`No data available for ${m} on ${bench}`}
                      >
                        <span className="text-(--color-text-dim) opacity-40 font-mono text-xs">
                          —
                        </span>
                      </td>
                    );
                  }
                  const [passAtK, passed, total] = cell;
                  const pct = Math.round(passAtK * 1000) / 10;
                  const { label, title: reliabilityTitle } =
                    classifyReliability(passAtK);
                  return (
                    <td
                      key={m}
                      title={`${m} on ${bench}: ${passed}/${total} (${pct}%) — ${reliabilityTitle}`}
                    >
                      <a href={`/benchmarks/${bench}`} className="no-underline">
                        <Badge
                          variant="outline"
                          className="font-mono text-xs"
                          style={{
                            background: heatBg(passAtK),
                            color: heatColor(passAtK),
                            borderColor: `${heatColor(passAtK)}33`,
                          }}
                        >
                          {passed}/{total}
                        </Badge>
                        <span className="font-mono text-[0.65rem] text-(--color-text-dim) ml-1">
                          {label}
                        </span>
                      </a>
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
