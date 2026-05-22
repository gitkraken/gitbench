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
  passRateMetric,
} from "@/components/charts/model-groups";
import {
  ProviderLegend,
  VerticalGroupTick,
  formatCompactDecimal,
  paddedDomain,
  rowMap,
  tooltipStyle,
} from "@/components/charts/grouped-chart-ui";

export default function PassRateBarChart() {
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
      passRateMetric,
      "max",
    ).sort((a, b) => b.representativeValue - a.representativeValue);
  }, [data, selectedGroups]);

  const rowsById = useMemo(() => rowMap(chartData), [chartData]);
  const yDomain = useMemo(
    () => paddedDomain(chartData, [0, 100], { floor: 0, ceiling: 100 }),
    [chartData],
  );

  if (!data) return <div>Loading...</div>;

  return (
    <div>
      <div className="max-w-xs ml-auto w-full mb-3">
        <ModelSelector value={selectedGroups} onChange={setSelectedGroups} />
      </div>
      <div
        className="card"
        title="Pass rate percentages for each model across all 204 Git fixtures. Higher bars = better Git skills."
      >
        <ResponsiveContainer width="100%" height={350}>
          <BarChart
            data={chartData}
            layout="horizontal"
            margin={{ top: 5, right: 20, left: 0, bottom: 58 }}
          >
            <CartesianGrid vertical={false} stroke="rgba(255,255,255,0.04)" />
            <XAxis
              type="category"
              dataKey="id"
              tick={(props: any) => (
                <VerticalGroupTick {...props} rowMap={rowsById} />
              )}
              axisLine={false}
              tickLine={false}
              interval={0}
              height={62}
            />
            <YAxis
              type="number"
              domain={yDomain}
              tick={{
                fill: "var(--text-dim)",
                fontSize: 11,
                fontFamily: "var(--font-mono)",
              }}
              tickFormatter={(value: number) =>
                `${formatCompactDecimal(value, 2)}%`
              }
              axisLine={false}
              tickLine={false}
            />
            <Bar
              dataKey="range"
              radius={[4, 4, 4, 4]}
              barSize={Math.max(
                12,
                Math.min(28, 400 / Math.max(1, chartData.length)),
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
                <Cell key={entry.id} fill={getProviderColor(entry.provider)} />
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
                        {effort.value.toFixed(1)}%
                        {effort.modelName ===
                        entry.representativeEffort.modelName
                          ? " (best)"
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
                      Pass rate = % of 204 Git fixtures answered correctly.
                      Higher reasoning levels typically score better.
                    </div>
                  </div>
                );
              }}
            />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <ProviderLegend rows={chartData} />
    </div>
  );
}
