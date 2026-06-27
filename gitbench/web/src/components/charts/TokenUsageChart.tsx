import { useEffect, useMemo, useState } from "react";
import type { GitBenchData } from "@/lib/types";
import { loadTokenChart } from "@/lib/report-client";
import ProviderIcon from "@/components/ProviderIcon";
import ModelOutputControls from "@/components/charts/ModelOutputControls";
import { useSyncedModelSelection } from "@/components/charts/useSyncedModelSelection";
import { buildTokenUsageRows } from "@/components/charts/model-groups";
import {
  GroupedMetricTooltipSections,
  VerticalGroupedMetricChart,
  formatCompactDecimal,
  tooltipStyle,
  zeroAnchoredDomain,
} from "@/components/charts/grouped-chart-ui";

function formatTokens(value: number): string {
  if (value >= 1_000_000)
    return `${formatCompactDecimal(value / 1_000_000, 2)}M`;
  if (value >= 1_000) return `${formatCompactDecimal(value / 1_000, 2)}K`;
  return formatCompactDecimal(value, 2);
}

import { useCampaignId } from "@/lib/use-campaign";

export default function TokenUsageChart() {
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
    loadTokenChart().then(setData);
  }, [campaignId]);

  const chartData = useMemo(() => {
    if (!data) return [];
    return buildTokenUsageRows(data, selectedGroups, outputMode).sort(
      (a, b) => a.sortValue - b.sortValue
    );
  }, [data, selectedGroups, outputMode]);

  const yDomain = useMemo(
    () => zeroAnchoredDomain(chartData, [0, 1]),
    [chartData]
  );
  const allZero =
    chartData.length === 0 || chartData.every((row) => row.maxValue === 0);

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
      {allZero ? (
        <div className="card p-8 text-center">
          <div className="font-display text-base text-(--text-dim) mb-1">
            No token data available
          </div>
          <div className="font-mono text-xs text-(--text-dim) opacity-60">
            Token usage data was not collected for these benchmark runs.
          </div>
        </div>
      ) : (
        <VerticalGroupedMetricChart
          rows={chartData}
          outputMode={outputMode}
          yDomain={yDomain}
          yTickFormatter={formatTokens}
          yAxisLabel="Tokens"
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
                formatRepresentative={formatTokens}
                renderEffort={(effort) => (
                  <span style={{ color: "var(--text-dim)" }}>
                    {effort.reasoningLevel ?? "default"}:{" "}
                    {formatTokens(effort.value)}
                    {effort.inputTokens || effort.outputTokens
                      ? ` (in ${formatTokens(
                          effort.inputTokens ?? 0
                        )} / out ${formatTokens(effort.outputTokens ?? 0)}${
                          effort.reasoningTokens != null
                            ? ` (${formatTokens(
                                effort.reasoningTokens
                              )} reasoning within output)`
                            : ""
                        })`
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
                Input + visible output + reasoning = total tokens. Fewer is more
                efficient.
              </div>
            </div>
          )}
        />
      )}
    </div>
  );
}
