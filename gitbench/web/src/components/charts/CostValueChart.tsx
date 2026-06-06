import { useEffect, useMemo, useState } from "react";
import type { GitBenchData } from "@/lib/types";
import { loadCostChart } from "@/lib/report-client";
import ProviderIcon from "@/components/ProviderIcon";
import ModelSelector from "@/components/charts/ModelSelector";
import OutputModeSelector from "@/components/charts/OutputModeSelector";
import { useSyncedModelSelection } from "@/components/charts/useSyncedModelSelection";
import {
  buildGroupedMetricRows,
  costMetric,
  writeStoredOutputMode,
} from "@/components/charts/model-groups";
import {
  VerticalGroupedMetricChart,
  formatCompactDecimal,
  tooltipStyle,
  zeroAnchoredDomain,
} from "@/components/charts/grouped-chart-ui";

function formatCost(value: number): string {
  if (value < 0.0001) return `$${value.toExponential(1)}`;
  if (value < 0.01) return `$${formatCompactDecimal(value, 3)}`;
  return `$${formatCompactDecimal(value, 2)}`;
}

export default function CostValueChart() {
  const [data, setData] = useState<GitBenchData | null>(null);
  const {
    selectedGroups,
    setSelectedGroups,
    outputMode,
    setOutputMode,
    availableOutputModes,
  } = useSyncedModelSelection(data);

  useEffect(() => {
    loadCostChart().then(setData);
  }, []);

  const chartData = useMemo(() => {
    if (!data) return [];
    return buildGroupedMetricRows(
      data,
      selectedGroups,
      costMetric,
      "median",
      outputMode,
    ).sort((a, b) => a.representativeValue - b.representativeValue);
  }, [data, selectedGroups, outputMode]);

  const yDomain = useMemo(
    () => zeroAnchoredDomain(chartData, [0, 1]),
    [chartData],
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
          yDomain={yDomain}
          yTickFormatter={formatCost}
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
              {entry.efforts.map((effort) => (
                <div
                  key={effort.modelName}
                  style={{ color: "var(--text-dim)" }}
                >
                  {effort.reasoningLevel ?? "default"}:{" "}
                  {formatCost(effort.value)}
                  {effort.passRate != null
                    ? `, pass ${(effort.passRate * 100).toFixed(1)}%`
                    : ""}
                  {effort.value === entry.representativeValue
                    ? " (median)"
                    : ""}
                </div>
              ))}
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
