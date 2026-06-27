import { useEffect, useMemo, useState } from "react";
import type { GitBenchData } from "@/lib/types";
import { loadCostChart } from "@/lib/report-client";
import ProviderIcon from "@/components/ProviderIcon";
import ModelOutputControls from "@/components/charts/ModelOutputControls";
import { useSyncedModelSelection } from "@/components/charts/useSyncedModelSelection";
import {
  buildGroupedMetricRows,
  costMetric,
} from "@/components/charts/model-groups";
import {
  GroupedMetricTooltipSections,
  VerticalGroupedMetricChart,
  tooltipStyle,
  zeroAnchoredDomain,
} from "@/components/charts/grouped-chart-ui";

const costFormatter = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  minimumFractionDigits: 0,
  maximumFractionDigits: 4,
});

export function formatCost(value: number): string {
  if (!Number.isFinite(value)) return "\u2014";
  return costFormatter.format(value);
}

import { useCampaignId } from "@/lib/use-campaign";

export default function CostValueChart() {
  const [data, setData] = useState<GitBenchData | null>(null);
  const campaignId = useCampaignId();
  const {
    selectedGroups,
    setSelectedGroups,
    outputMode,
    setOutputMode,
    availableOutputModes,
  } = useSyncedModelSelection(data);

  useEffect(() => {
    loadCostChart().then(setData);
  }, [campaignId]);

  const chartData = useMemo(() => {
    if (!data) return [];
    return buildGroupedMetricRows(
      data,
      selectedGroups,
      costMetric,
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
      <ModelOutputControls
        data={data}
        selectedGroups={selectedGroups}
        onSelectedGroupsChange={setSelectedGroups}
        outputMode={outputMode}
        onOutputModeChange={setOutputMode}
        availableOutputModes={availableOutputModes}
      />
      {chartData.length === 0 ? (
        <div className="card p-8 text-center">
          <div className="font-display text-base text-(--text-dim) mb-1">
            No pricing data available
          </div>
          <div className="font-mono text-xs text-(--text-dim) opacity-60">
            Run benchmarks through OpenRouter to collect cost data for each
            model.
          </div>
        </div>
      ) : (
        <VerticalGroupedMetricChart
          rows={chartData}
          outputMode={outputMode}
          yDomain={yDomain}
          yTickFormatter={formatCost}
          yAxisLabel="Cost (USD)"
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
                formatRepresentative={formatCost}
                renderEffort={(effort) => (
                  <span style={{ color: "var(--text-dim)" }}>
                    {effort.reasoningLevel ?? "default"}:{" "}
                    {formatCost(effort.value)}
                    {effort.passRate != null
                      ? `, pass ${(effort.passRate * 100).toFixed(1)}%`
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
                API cost for 204-fixture run. - = local/Ollama
              </div>
            </div>
          )}
        />
      )}
    </div>
  );
}
