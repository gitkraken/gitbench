import { useEffect, useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { GitBenchData } from "@/lib/types";
import { loadData } from "@/lib/load-data";
import { modelGroupPath } from "@/lib/routes";
import { getProviderColor } from "@/lib/provider-colors";
import ProviderIcon from "@/components/ProviderIcon";
import ModelSelector from "@/components/charts/ModelSelector";
import { useSyncedModelSelection } from "@/components/charts/useSyncedModelSelection";
import {
  buildGroupedMetricRows,
  tokenMetric,
} from "@/components/charts/model-groups";
import {
  HorizontalGroupTick,
  ProviderLegend,
  formatCompactDecimal,
  paddedDomain,
  rowMap,
  tooltipStyle,
} from "@/components/charts/grouped-chart-ui";

function formatTokens(value: number): string {
  if (value >= 1_000_000)
    return `${formatCompactDecimal(value / 1_000_000, 2)}M`;
  if (value >= 1_000) return `${formatCompactDecimal(value / 1_000, 2)}K`;
  return formatCompactDecimal(value, 2);
}

export default function TokenUsageChart() {
  const [data, setData] = useState<GitBenchData | null>(null);
  const { selectedGroups, setSelectedGroups } = useSyncedModelSelection(data);

  useEffect(() => {
    loadData().then(setData);
  }, []);

  const chartData = useMemo(() => {
    if (!data) return [];
    return buildGroupedMetricRows(
      data,
      selectedGroups,
      tokenMetric,
      "min",
    ).sort((a, b) => a.representativeValue - b.representativeValue);
  }, [data, selectedGroups]);

  const rowsById = useMemo(() => rowMap(chartData), [chartData]);
  const xDomain = useMemo(
    () => paddedDomain(chartData, [0, 1], { floor: 0 }),
    [chartData],
  );
  const allZero =
    chartData.length === 0 || chartData.every((row) => row.maxValue === 0);

  if (!data) return <div>Loading...</div>;

  return (
    <div>
      <div className="max-w-xs ml-auto w-full mb-3">
        <ModelSelector value={selectedGroups} onChange={setSelectedGroups} />
      </div>
      {allZero ? (
        <div className="card p-8 text-center">
          <div className="font-display text-base text-[var(--text-dim)] mb-1">
            No token data available
          </div>
          <div className="font-mono text-xs text-[var(--text-dim)] opacity-60">
            Token usage data was not collected for these benchmark runs.
          </div>
        </div>
      ) : (
        <>
          <div
            className="card"
            title="Total tokens (input + output) consumed across all 204 fixture evaluations. Less output for same accuracy = more efficient."
          >
            <ResponsiveContainer width="100%" height={350}>
              <BarChart
                data={chartData}
                layout="vertical"
                margin={{ top: 5, right: 20, left: 0, bottom: 5 }}
              >
                <CartesianGrid
                  horizontal={false}
                  stroke="rgba(255,255,255,0.04)"
                />
                <XAxis
                  type="number"
                  domain={xDomain}
                  tick={{
                    fill: "var(--text-dim)",
                    fontSize: 11,
                    fontFamily: "var(--font-mono)",
                  }}
                  tickFormatter={formatTokens}
                  axisLine={false}
                  tickLine={false}
                />
                <YAxis
                  type="category"
                  dataKey="id"
                  tick={(props: any) => (
                    <HorizontalGroupTick {...props} rowMap={rowsById} />
                  )}
                  axisLine={false}
                  tickLine={false}
                  interval={0}
                  width={112}
                />
                <Bar
                  dataKey="range"
                  radius={[4, 4, 4, 4]}
                  barSize={Math.max(
                    12,
                    Math.min(28, 300 / Math.max(1, chartData.length)),
                  )}
                  cursor="pointer"
                  onClick={(entry: any) => {
                    if (entry?.provider && entry?.baseModel) {
                      window.location.href = modelGroupPath(
                        entry.provider,
                        entry.baseModel,
                      );
                    }
                  }}
                >
                  {chartData.map((entry) => (
                    <Cell
                      key={entry.id}
                      fill={getProviderColor(entry.provider)}
                    />
                  ))}
                </Bar>
                <Tooltip
                  cursor={{ fill: "rgba(255,255,255,0.04)" }}
                  content={({ active, label }) => {
                    if (!active || !label) return null;
                    const entry = rowsById[String(label)];
                    if (!entry) return null;
                    return (
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
                            {formatTokens(effort.value)}
                            {effort.inputTokens || effort.outputTokens
                              ? `, in ${formatTokens(
                                  effort.inputTokens ?? 0,
                                )} / out ${formatTokens(
                                  effort.outputTokens ?? 0,
                                )}`
                              : ""}
                            {effort.modelName ===
                            entry.representativeEffort.modelName
                              ? " (lowest tokens)"
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
                          Total tokens (input + output) across all 204 fixtures.
                          Less output for same accuracy = more efficient.
                        </div>
                      </div>
                    );
                  }}
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <ProviderLegend rows={chartData} />
        </>
      )}
    </div>
  );
}
