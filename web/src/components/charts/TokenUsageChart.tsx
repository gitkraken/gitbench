import { useEffect, useMemo, useState } from "react";
import type { GitBenchData } from "@/lib/types";
import { loadTokenChart } from "@/lib/report-client";
import ProviderIcon from "@/components/ProviderIcon";
import ModelOutputControls from "@/components/charts/ModelOutputControls";
import { useSyncedModelSelection } from "@/components/charts/useSyncedModelSelection";
import {
  buildTokenUsageRows,
  sortGroupedMetricRowsDescending,
} from "@/components/charts/model-groups";
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

function formatTooltipTokens(value: number): string {
  if (value >= 1_000_000)
    return `${formatCompactDecimal(value / 1_000_000, 0)}M`;
  if (value >= 1_000) return `${formatCompactDecimal(value / 1_000, 0)}K`;
  return formatCompactDecimal(value, 0);
}

const INPUT_COLOR = "#aeb6c2";
const OUTPUT_COLOR = "#5ec4b6";
const REASONING_COLOR = "#e9b44c";
const OVERFLOW_COLOR = "#f07878";

import { useCampaignId } from "@/lib/use-campaign";

interface ScopedChartProps {
  benchmarkName?: string;
  fixtureId?: string;
}

export default function TokenUsageChart({
  benchmarkName,
  fixtureId,
}: ScopedChartProps = {}) {
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
    loadTokenChart({ benchmark: benchmarkName, fixture: fixtureId }).then(
      setData,
    );
  }, [benchmarkName, fixtureId, campaignId]);

  const chartData = useMemo(() => {
    if (!data) return [];
    return sortGroupedMetricRowsDescending(
      buildTokenUsageRows(data, selectedGroups, outputMode),
    );
  }, [data, selectedGroups, outputMode]);

  const yDomain = useMemo(
    () => zeroAnchoredDomain(chartData, [0, 1]),
    [chartData],
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
          renderTooltip={(entry) => {
            const hasOverflow = Object.values(entry.modes).some((summary) =>
              summary?.efforts.some(
                (effort) => (effort.reasoningOverflowTokens ?? 0) > 0,
              ),
            );
            return (
              <div style={{ ...tooltipStyle, maxWidth: 300 }}>
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
                <div
                  style={{
                    color: "var(--text-dim)",
                    fontSize: 10,
                    whiteSpace: "nowrap",
                  }}
                >
                  Total · (<span style={{ color: INPUT_COLOR }}>in</span> /{" "}
                  <span style={{ color: OUTPUT_COLOR }}>out</span> /{" "}
                  <span style={{ color: REASONING_COLOR }}>reasoning</span>)
                </div>
                <GroupedMetricTooltipSections
                  entry={entry}
                  outputMode={outputMode}
                  formatRepresentative={formatTokens}
                  renderEffort={(effort) => {
                    const hasUsage =
                      effort.inputTokens != null || effort.outputTokens != null;
                    return (
                      <span
                        style={{
                          color: "var(--text-dim)",
                          display: "block",
                          fontSize: 12,
                          whiteSpace: "nowrap",
                        }}
                      >
                        {effort.reasoningLevel ?? "default"}:{" "}
                        {formatTooltipTokens(effort.value)}
                        {hasUsage ? (
                          <>
                            {" · ("}
                            <span style={{ color: INPUT_COLOR }}>
                              {formatTooltipTokens(effort.inputTokens ?? 0)}
                            </span>
                            {" / "}
                            <span style={{ color: OUTPUT_COLOR }}>
                              {effort.outputTokens == null
                                ? "—"
                                : formatTooltipTokens(effort.outputTokens)}
                            </span>
                            {" / "}
                            <span style={{ color: REASONING_COLOR }}>
                              {effort.reasoningTokens == null
                                ? "—"
                                : formatTooltipTokens(
                                    effort.reasoningWithinOutputTokens ?? 0,
                                  )}
                            </span>
                            {(effort.reasoningOverflowTokens ?? 0) > 0 ? (
                              <span style={{ color: OVERFLOW_COLOR }}>
                                +
                                {formatTooltipTokens(
                                  effort.reasoningOverflowTokens ?? 0,
                                )}
                                *
                              </span>
                            ) : null}
                            {`)`}
                          </>
                        ) : null}
                      </span>
                    );
                  }}
                />
                {hasOverflow ? (
                  <div
                    style={{
                      color: OVERFLOW_COLOR,
                      fontSize: 10,
                      marginTop: 5,
                    }}
                  >
                    * provider-reported reasoning overflow
                  </div>
                ) : null}
              </div>
            );
          }}
        />
      )}
    </div>
  );
}
