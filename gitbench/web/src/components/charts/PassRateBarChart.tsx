import { useEffect, useMemo, useState } from "react";
import type { GitBenchData } from "@/lib/types";
import { loadPassRateChart } from "@/lib/report-client";
import ProviderIcon from "@/components/ProviderIcon";
import ModelSelector from "@/components/charts/ModelSelector";
import OutputModeSelector from "@/components/charts/OutputModeSelector";
import { useSyncedModelSelection } from "@/components/charts/useSyncedModelSelection";
import {
  buildGroupedMetricRows,
  passRateMetric,
  benchPassRateMetric,
  writeStoredOutputMode,
} from "@/components/charts/model-groups";
import {
  GroupedMetricTooltipSections,
  VerticalGroupedMetricChart,
  formatCompactDecimal,
  tooltipStyle,
  zeroAnchoredDomain,
} from "@/components/charts/grouped-chart-ui";

interface PassRateBarChartProps {
  benchmarkName?: string;
}

export default function PassRateBarChart({
  benchmarkName,
}: PassRateBarChartProps = {}) {
  const [data, setData] = useState<GitBenchData | null>(null);
  const {
    selectedGroups,
    setSelectedGroups,
    outputMode,
    setOutputMode,
    availableOutputModes,
  } = useSyncedModelSelection(data);

  useEffect(() => {
    loadPassRateChart(benchmarkName).then(setData);
  }, [benchmarkName]);

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
      <VerticalGroupedMetricChart
        rows={chartData}
        outputMode={outputMode}
        yDomain={yDomain}
        yTickFormatter={(value) => `${formatCompactDecimal(value, 2)}%`}
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
          </div>
        )}
      />
    </div>
  );
}
