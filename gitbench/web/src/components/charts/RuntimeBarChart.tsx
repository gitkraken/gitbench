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
import ModelSelector from "./ModelSelector";
import { useSyncedModelSelection } from "./useSyncedModelSelection";
import { buildGroupedMetricRows, runtimeMetric } from "./model-groups";
import {
  HorizontalGroupTick,
  ProviderLegend,
  formatCompactDecimal,
  paddedDomain,
  rowMap,
  tooltipStyle,
} from "./grouped-chart-ui";

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
  const { selectedGroups, setSelectedGroups } = useSyncedModelSelection(data);

  useEffect(() => {
    loadData().then(setData);
  }, []);

  const chartData = useMemo(() => {
    if (!data) return [];
    return buildGroupedMetricRows(data, selectedGroups, runtimeMetric, "min").sort(
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
            No runtime data available
          </div>
          <div className="font-mono text-xs text-[var(--text-dim)] opacity-60">
            Runtime data was not collected for these benchmark runs.
          </div>
        </div>
      ) : (
        <>
          <div className="card">
            <ResponsiveContainer width="100%" height={350}>
              <BarChart
                data={chartData}
                layout="vertical"
                margin={{ top: 5, right: 20, left: 128, bottom: 5 }}
              >
                <CartesianGrid horizontal={false} stroke="rgba(255,255,255,0.04)" />
                <XAxis
                  type="number"
                  domain={xDomain}
                  tick={{ fill: "var(--text-dim)", fontSize: 11, fontFamily: "var(--font-mono)" }}
                  tickFormatter={formatAxis}
                  axisLine={false}
                  tickLine={false}
                />
                <YAxis
                  type="category"
                  dataKey="id"
                  tick={(props: any) => <HorizontalGroupTick {...props} rowMap={rowsById} />}
                  axisLine={false}
                  tickLine={false}
                  interval={0}
                  width={128}
                />
                <Bar
                  dataKey="range"
                  radius={[4, 4, 4, 4]}
                  barSize={Math.max(12, Math.min(28, 300 / Math.max(1, chartData.length)))}
                  cursor="pointer"
                  onClick={(entry: any) => {
                    if (entry?.provider && entry?.baseModel) {
                      window.location.href = modelGroupPath(entry.provider, entry.baseModel);
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
                          <div key={effort.modelName} style={{ color: "var(--text-dim)" }}>
                            {effort.reasoningLevel ?? "default"}: {formatRuntime(effort.value)}
                            {effort.avgMs ? `, avg ${(effort.avgMs / 1000).toFixed(1)}s` : ""}
                            {effort.modelName === entry.representativeEffort.modelName ? " (fastest)" : ""}
                          </div>
                        ))}
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
