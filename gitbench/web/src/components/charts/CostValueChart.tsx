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
  costMetric,
} from "@/components/charts/model-groups";
import {
  HorizontalGroupTick,
  ProviderLegend,
  formatCompactDecimal,
  paddedDomain,
  rowMap,
  tooltipStyle,
} from "@/components/charts/grouped-chart-ui";

function formatCost(value: number): string {
  if (value < 0.0001) return `$${value.toExponential(1)}`;
  if (value < 0.01) return `$${formatCompactDecimal(value, 3)}`;
  return `$${formatCompactDecimal(value, 2)}`;
}

export default function CostValueChart() {
  const [data, setData] = useState<GitBenchData | null>(null);
  const { selectedGroups, setSelectedGroups } = useSyncedModelSelection(data);

  useEffect(() => {
    loadData().then(setData);
  }, []);

  const chartData = useMemo(() => {
    if (!data) return [];
    return buildGroupedMetricRows(data, selectedGroups, costMetric, "min").sort(
      (a, b) => a.representativeValue - b.representativeValue,
    );
  }, [data, selectedGroups]);

  const rowsById = useMemo(() => rowMap(chartData), [chartData]);
  const xDomain = useMemo(
    () => paddedDomain(chartData, [0, 1], { floor: 0 }),
    [chartData],
  );

  if (!data) return <div>Loading...</div>;

  return (
    <div>
      <div className="max-w-xs ml-auto w-full mb-3">
        <ModelSelector value={selectedGroups} onChange={setSelectedGroups} />
      </div>
      {chartData.length === 0 ? (
        <div className="card p-8 text-center">
          <div className="font-display text-base text-[var(--text-dim)] mb-1">
            No pricing data available
          </div>
          <div className="font-mono text-xs text-[var(--text-dim)] opacity-60">
            Run benchmarks through OpenRouter to collect cost data for each
            model.
          </div>
        </div>
      ) : (
        <>
          <div
            className="card"
            title="Total API cost (USD) to evaluate each model across all 204 fixtures. — means local/Ollama (no cost tracked)."
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
                  tickFormatter={formatCost}
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
                            {formatCost(effort.value)}
                            {effort.passRate != null
                              ? `, pass ${(effort.passRate * 100).toFixed(1)}%`
                              : ""}
                            {effort.modelName ===
                            entry.representativeEffort.modelName
                              ? " (lowest cost)"
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
                          Total API cost (USD) across all 204 fixtures. — means
                          local/Ollama (no cost tracked).
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
