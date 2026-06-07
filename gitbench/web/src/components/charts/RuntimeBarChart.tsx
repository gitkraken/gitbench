import { useEffect, useMemo, useState } from "react";
import type { GitBenchData } from "@/lib/types";
import { loadRuntimeChart } from "@/lib/report-client";
import ProviderIcon from "@/components/ProviderIcon";
import ModelSelector from "@/components/charts/ModelSelector";
import OutputModeSelector from "@/components/charts/OutputModeSelector";
import { useSyncedModelSelection } from "@/components/charts/useSyncedModelSelection";
import {
  buildGroupedMetricRows,
  runtimeMetric,
  writeStoredOutputMode,
} from "@/components/charts/model-groups";
import {
  GroupedMetricTooltipSections,
  VerticalGroupedMetricChart,
  formatCompactDecimal,
  tooltipStyle,
  zeroAnchoredDomain,
} from "@/components/charts/grouped-chart-ui";

function formatRuntime(seconds: number): string {
  if (seconds >= 60) {
    const mins = Math.floor(seconds / 60);
    const secs = Math.round(seconds % 60);
    return `${mins}m ${secs}s`;
  }
  if (seconds >= 1) return `${seconds.toFixed(1)}s`;
  return `${seconds.toFixed(2)}s`;
}

function formatAxis(seconds: number): string {
  if (seconds >= 60) return `${formatCompactDecimal(seconds / 60, 2)}m`;
  return `${formatCompactDecimal(seconds, 2)}s`;
}

export default function RuntimeBarChart() {
  const [data, setData] = useState<GitBenchData | null>(null);
  const {
    selectedGroups,
    setSelectedGroups,
    outputMode,
    setOutputMode,
    availableOutputModes,
  } = useSyncedModelSelection(data);

  useEffect(() => {
    loadRuntimeChart().then(setData);
  }, []);

  const chartData = useMemo(() => {
    if (!data) return [];
    return buildGroupedMetricRows(
      data,
      selectedGroups,
      runtimeMetric,
      "median",
      outputMode
    ).sort((a, b) => a.sortValue - b.sortValue);
  }, [data, selectedGroups, outputMode]);

  const yDomain = useMemo(
    () => zeroAnchoredDomain(chartData, [0, 1]),
    [chartData]
  );

  if (!data) return <div>Loading...</div>;

  return (
    <div>
      <div className="max-w-xs ml-auto w-full mb-3 flex items-center gap-3">
        <div className="flex-1">
          <ModelSelector
            data={data}
            value={selectedGroups}
            onChange={setSelectedGroups}
          />
        </div>
        <OutputModeSelector
          value={outputMode}
          onChange={(mode) => {
            setOutputMode(mode);
            writeStoredOutputMode(mode);
          }}
          availableModes={availableOutputModes}
        />
      </div>
      {chartData.length === 0 ? (
        <div className="card p-8 text-center">
          <div className="font-display text-base text-(--text-dim) mb-1">
            No API time data available
          </div>
          <div className="font-mono text-xs text-(--text-dim) opacity-60">
            API latency was not collected for these benchmark runs.
          </div>
        </div>
      ) : (
        <VerticalGroupedMetricChart
          rows={chartData}
          outputMode={outputMode}
          yDomain={yDomain}
          yTickFormatter={formatAxis}
          renderTooltip={(entry) => (
            <div style={tooltipStyle}>
              <div
                style={{
                  color: "var(--text)",
                  marginBottom: 4,
                  display: "flex",
                  alignItems: "center",
                  gap: 6,
                }}
              >
                <ProviderIcon provider={entry.provider} size={14} />
                {entry.provider}/{entry.baseModel}
              </div>
              <GroupedMetricTooltipSections
                entry={entry}
                outputMode={outputMode}
                formatRepresentative={formatRuntime}
                renderEffort={(effort) => (
                  <span style={{ color: "var(--text-dim)" }}>
                    {effort.reasoningLevel ?? "default"}:{" "}
                    {formatRuntime(effort.value)} API time
                    {effort.avgMs != null
                      ? `, avg API ${(effort.avgMs / 1000).toFixed(1)}s`
                      : ""}
                  </span>
                )}
              />
              <div
                style={{
                  borderTop: "1px solid rgba(255,255,255,0.06)",
                  margin: "6px 0",
                }}
              />
              <div
                style={{
                  color: "var(--text-dim)",
                  fontSize: 10,
                  lineHeight: 1.4,
                }}
              >
                API call latency. Lower is faster.
              </div>
            </div>
          )}
        />
      )}
    </div>
  );
}
