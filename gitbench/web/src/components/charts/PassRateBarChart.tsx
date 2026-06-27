import { useEffect, useMemo, useState } from "react";
import type { CampaignAwareGitBenchData } from "@/lib/types";
import { loadPassRateChart } from "@/lib/report-client";
import ProviderIcon from "@/components/ProviderIcon";
import ModelOutputControls from "@/components/charts/ModelOutputControls";
import { useSyncedModelSelection } from "@/components/charts/useSyncedModelSelection";
import {
  buildGroupedMetricRows,
  passRateMetric,
  benchPassRateMetric,
} from "@/components/charts/model-groups";
import {
  GroupedMetricTooltipSections,
  VerticalGroupedMetricChart,
  formatCompactDecimal,
  tooltipStyle,
  zeroAnchoredDomain,
} from "@/components/charts/grouped-chart-ui";

import { useCampaignId } from "@/lib/use-campaign";

interface PassRateBarChartProps {
  benchmarkName?: string;
  initialData?: CampaignAwareGitBenchData;
}

export default function PassRateBarChart({
  benchmarkName,
  initialData,
}: PassRateBarChartProps = {}) {
  const [data, setData] = useState<CampaignAwareGitBenchData | null>(
    initialData ?? null
  );
  const campaignId = useCampaignId();
  const {
    selectedGroups,
    setSelectedGroups,
    outputMode,
    setOutputMode,
    availableOutputModes,
  } = useSyncedModelSelection(data);

  useEffect(() => {
    if (initialData && !campaignId) return;
    loadPassRateChart(benchmarkName).then(setData);
  }, [benchmarkName, campaignId, initialData]);

  const chartData = useMemo(() => {
    if (!data) return [];
    const extractor = benchmarkName
      ? benchPassRateMetric(benchmarkName)
      : passRateMetric;
    return buildGroupedMetricRows(
      data,
      selectedGroups,
      extractor,
      "median",
      outputMode
    ).sort((a, b) => b.sortValue - a.sortValue);
  }, [data, selectedGroups, outputMode, benchmarkName]);

  const yDomain = useMemo(
    () => zeroAnchoredDomain(chartData, [0, 100], { ceiling: 100 }),
    [chartData]
  );

  const fixtureCount = useMemo(() => {
    if (!data || !benchmarkName) return 204;
    return Math.max(
      0,
      ...Object.values(data.matrix).map(
        (byBenchmark) => byBenchmark[benchmarkName]?.total ?? 0
      )
    );
  }, [data, benchmarkName]);

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
      <VerticalGroupedMetricChart
        rows={chartData}
        outputMode={outputMode}
        yDomain={yDomain}
        yTickFormatter={(value) => `${formatCompactDecimal(value, 2)}%`}
        yAxisLabel="Pass Rate (%)"
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
              formatRepresentative={(value) => `${value.toFixed(1)}%`}
              renderEffort={(effort) => (
                <span style={{ color: "var(--text-dim)" }}>
                  {effort.reasoningLevel ?? "default"}:{" "}
                  {effort.value.toFixed(1)}%
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
              % of {fixtureCount} fixture{fixtureCount !== 1 ? "s" : ""} passed
            </div>
            {data.campaign_metadata && (
              <div
                style={{
                  color: "var(--text-dim)",
                  fontSize: 10,
                  lineHeight: 1.4,
                  marginTop: 4,
                }}
              >
                Latest evaluation: {data.campaign_metadata.completed_trials}/
                {data.campaign_metadata.planned_trials} trials. Repeated-trial
                variability is shown in fixture detail.
              </div>
            )}
          </div>
        )}
      />
    </div>
  );
}
