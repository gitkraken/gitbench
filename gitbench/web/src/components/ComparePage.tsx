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
import ModelSelector, {
  defaultSelectionForCompare,
} from "@/components/charts/ModelSelector";
import OutputModeSelector from "@/components/charts/OutputModeSelector";
import ScatterPlot from "@/components/charts/ScatterPlot";
import { useSyncedModelSelection } from "@/components/charts/useSyncedModelSelection";
import {
  outputModeLabel,
  visibleOutputModes,
} from "@/components/charts/model-groups";
import {
  buildCompareBenchmarkData,
  buildCompareOverallRows,
  buildCompareReliabilityPair,
  compareBenchmarkPairValues,
  type CompareBenchmarkRow,
} from "@/components/charts/compare-chart-data";
import {
  getOutputModeBarStyle,
  OutputModeLegend,
  tooltipStyle,
} from "@/components/charts/grouped-chart-ui";
import {
  computeReliabilityDeltas,
  reliabilityDeltaSummary,
} from "@/lib/fixture-reliability";
import { Badge } from "@/components/ui/badge";

const COLORS = [
  "#B657FF",
  "#196FFF",
  "#01B7A1",
  "#EC7FFF",
  "#01FEE0",
  "#C170FF",
  "#6AB8FF",
  "#FEDC00",
];

function getColor(passRate: number): string {
  if (passRate >= 0.8) return "var(--color-pass)";
  if (passRate >= 0.5) return "var(--color-warn)";
  return "var(--color-fail)";
}

function CompareModelLegend({
  items,
}: {
  items: Array<{ id: string; label: string; color: string }>;
}) {
  if (items.length === 0) return null;
  return (
    <div className="mt-3 flex flex-wrap justify-center gap-x-4 gap-y-2 font-mono text-[0.625rem] text-(--text-dim)">
      {items.map((item) => (
        <span key={item.id} className="inline-flex items-center gap-1.5">
          <span
            className="h-2 w-2 rounded-full"
            style={{ backgroundColor: item.color }}
          />
          {item.label}
        </span>
      ))}
    </div>
  );
}

export default function ComparePage() {
  const [data, setData] = useState<GitBenchData | null>(null);
  const defaultSelectedGroups = useMemo(
    () => (data ? defaultSelectionForCompare(data) : []),
    [data]
  );
  const {
    selectedGroups,
    setSelectedGroups,
    selectedModels,
    outputMode,
    setOutputMode,
    availableOutputModes,
  } = useSyncedModelSelection(data, {
    defaultSelectedGroups,
    defaultOutputMode: "both",
  });

  useEffect(() => {
    loadData().then(setData);
  }, []);

  const overallData = useMemo(
    () => (data ? buildCompareOverallRows(data, selectedModels) : []),
    [data, selectedModels]
  );
  const overallById = useMemo(
    () => new Map(overallData.map((row) => [row.id, row])),
    [overallData]
  );
  const benchmarkChart = useMemo(
    () =>
      data
        ? buildCompareBenchmarkData(data, selectedModels, outputMode, COLORS)
        : {
            pairs: [],
            rows: [],
            series: [],
            seriesByDataKey: new Map(),
          },
    [data, selectedModels, outputMode]
  );
  const compareLegendItems = useMemo(
    () =>
      benchmarkChart.pairs.map((pair, index) => ({
        id: pair.id,
        label: pair.label,
        color: COLORS[index % COLORS.length],
      })),
    [benchmarkChart.pairs]
  );
  const reliabilityPair = useMemo(
    () =>
      data
        ? buildCompareReliabilityPair(data, selectedGroups, outputMode)
        : [],
    [data, selectedGroups, outputMode]
  );
  const reliabilityDeltas = useMemo(
    () =>
      data && reliabilityPair.length >= 2
        ? computeReliabilityDeltas(data, reliabilityPair[0], reliabilityPair[1])
        : [],
    [data, reliabilityPair]
  );
  const reliabilitySummary = useMemo(
    () => reliabilityDeltaSummary(reliabilityDeltas),
    [reliabilityDeltas]
  );

  if (!data) return <div>Loading...</div>;

  return (
    <div>
      <div className="max-w-xs ml-auto w-full mb-6 flex items-center gap-3">
        <div className="flex-1">
          <ModelSelector
            data={data}
            value={selectedGroups}
            onChange={setSelectedGroups}
          />
        </div>
        <OutputModeSelector
          value={outputMode}
          onChange={setOutputMode}
          availableModes={availableOutputModes}
        />
      </div>

      <section className="mb-10">
        <div className="section-label">
          <span>Fixture Reliability Delta</span>
        </div>
        <div className="card p-5">
          {reliabilityPair.length < 2 ? (
            <p className="text-sm text-(--color-text-mid)">
              Select at least two models to compare fixture reliability.
            </p>
          ) : (
            <>
              <div className="grid grid-cols-4 gap-3 mb-5">
                <div className="bg-pass-bg/30 rounded-md p-3 text-center">
                  <div className="text-lg font-bold text-pass">
                    {reliabilitySummary.aMore}
                  </div>
                  <div className="text-[0.6rem] font-mono text-pass opacity-70">
                    More reliable
                  </div>
                  <div className="text-[0.55rem] font-mono text-(--color-text-dim) opacity-50">
                    {reliabilityPair[0]}
                  </div>
                </div>
                <div className="bg-fail-bg/30 rounded-md p-3 text-center">
                  <div className="text-lg font-bold text-fail">
                    {reliabilitySummary.bMore}
                  </div>
                  <div className="text-[0.6rem] font-mono text-fail opacity-70">
                    More reliable
                  </div>
                  <div className="text-[0.55rem] font-mono text-(--color-text-dim) opacity-50">
                    {reliabilityPair[1]}
                  </div>
                </div>
                <div className="bg-(--color-card) rounded-md p-3 text-center">
                  <div className="text-lg font-bold text-(--color-text-mid)">
                    {reliabilitySummary.equal}
                  </div>
                  <div className="text-[0.6rem] font-mono text-(--color-text-dim)">
                    Equal reliability
                  </div>
                </div>
                <div className="bg-(--color-card) rounded-md p-3 text-center">
                  <div className="text-lg font-bold text-(--color-text-dim)">
                    {reliabilitySummary.unknown}
                  </div>
                  <div className="text-[0.6rem] font-mono text-(--color-text-dim)">
                    Unknown
                  </div>
                </div>
              </div>
              {reliabilityDeltas.filter(
                (d) =>
                  d.classification !== "equal" && d.classification !== "unknown"
              ).length > 0 && (
                <div className="overflow-x-auto">
                  <table className="w-full text-left font-mono text-[0.65rem]">
                    <thead>
                      <tr className="text-(--color-text-dim) border-b border-border">
                        <th className="pb-1.5 pr-3 font-normal">Fixture</th>
                        <th className="pb-1.5 pr-3 font-normal text-right">
                          {reliabilityPair[0]}
                        </th>
                        <th className="pb-1.5 pr-3 font-normal text-right">
                          {reliabilityPair[1]}
                        </th>
                        <th className="pb-1.5 font-normal text-right">Delta</th>
                      </tr>
                    </thead>
                    <tbody>
                      {reliabilityDeltas
                        .filter(
                          (d) =>
                            d.classification !== "equal" &&
                            d.classification !== "unknown"
                        )
                        .slice(0, 20)
                        .map((d) => (
                          <tr
                            key={`${d.benchmark}/${d.fixtureId}`}
                            className="border-b border-(--color-border-dim)"
                          >
                            <td className="py-1.5 pr-3">
                              <a
                                href={`/fixtures/${d.benchmark}/${d.fixtureId}`}
                                className="text-accent hover:underline"
                              >
                                {d.fixtureId}
                              </a>
                            </td>
                            <td className="py-1.5 pr-3 text-right">
                              {d.a?.ratio != null
                                ? `${(d.a.ratio * 100).toFixed(0)}% (${
                                    d.a.passCount
                                  }/${d.a.validCount})`
                                : "—"}
                            </td>
                            <td className="py-1.5 pr-3 text-right">
                              {d.b?.ratio != null
                                ? `${(d.b.ratio * 100).toFixed(0)}% (${
                                    d.b.passCount
                                  }/${d.b.validCount})`
                                : "—"}
                            </td>
                            <td
                              className={`py-1.5 text-right font-medium ${
                                (d.delta ?? 0) > 0
                                  ? "text-pass"
                                  : (d.delta ?? 0) < 0
                                  ? "text-fail"
                                  : "text-(--color-text-dim)"
                              }`}
                            >
                              {d.delta != null
                                ? `${d.delta >= 0 ? "+" : ""}${(
                                    d.delta * 100
                                  ).toFixed(0)}%`
                                : "—"}
                            </td>
                          </tr>
                        ))}
                    </tbody>
                  </table>
                </div>
              )}
            </>
          )}
        </div>
      </section>

      <section className="mb-10">
        <div className="section-label">
          <span>Overall Pass Rates</span>
        </div>
        <div className="card">
          <ResponsiveContainer
            width="100%"
            height={Math.max(180, overallData.length * 42)}
          >
            <BarChart
              data={overallData}
              layout="vertical"
              margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
              barGap={2}
              barCategoryGap="24%"
            >
              <CartesianGrid
                horizontal={false}
                stroke="rgba(255,255,255,0.04)"
              />
              <XAxis
                type="number"
                domain={[0, 100]}
                tick={{
                  fill: "var(--text-dim)",
                  fontSize: 11,
                  fontFamily: "var(--font-mono)",
                }}
                tickFormatter={(v: number) => `${v}%`}
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                type="category"
                dataKey="id"
                tick={{
                  fill: "var(--text-mid)",
                  fontSize: 11,
                  fontFamily: "var(--font-mono)",
                }}
                tickFormatter={(value: string) =>
                  overallById.get(value)?.label ?? value
                }
                axisLine={false}
                tickLine={false}
                width={190}
              />
              {visibleOutputModes(outputMode).map((mode) => (
                <Bar
                  key={mode}
                  dataKey={mode === "text" ? "textPassRate" : "jsonPassRate"}
                  name={outputModeLabel(mode)}
                  barSize={outputMode === "both" ? 9 : 16}
                  isAnimationActive={false}
                >
                  {overallData.map((entry) => {
                    const raw = mode === "text" ? entry.textRaw : entry.jsonRaw;
                    const style = getOutputModeBarStyle(
                      getColor(raw ?? 0),
                      mode
                    );
                    return (
                      <Cell
                        key={`${entry.id}-${mode}`}
                        fill={style.fill}
                        fillOpacity={style.fillOpacity}
                        stroke={style.stroke}
                        strokeWidth={style.strokeWidth}
                      />
                    );
                  })}
                </Bar>
              ))}
              <Tooltip
                shared
                cursor={{ fill: "rgba(255,255,255,0.04)" }}
                content={({ active, label }) => {
                  const row = overallById.get(String(label));
                  if (!active || !row) return null;
                  return (
                    <div style={tooltipStyle}>
                      <div style={{ color: "var(--text)", marginBottom: 4 }}>
                        {row.label}
                      </div>
                      {visibleOutputModes(outputMode).map((mode) => {
                        const value =
                          mode === "text" ? row.textPassRate : row.jsonPassRate;
                        return (
                          <div key={mode} style={{ marginTop: 5 }}>
                            <span style={{ color: "var(--text-mid)" }}>
                              {outputModeLabel(mode)}:{" "}
                            </span>
                            <span style={{ color: "var(--text-dim)" }}>
                              {value == null ? "No data" : `${value}%`}
                            </span>
                          </div>
                        );
                      })}
                    </div>
                  );
                }}
              />
            </BarChart>
          </ResponsiveContainer>
        </div>
        <OutputModeLegend outputMode={outputMode} />
      </section>

      <section className="mb-10">
        <div className="section-label">
          <span>By Benchmark</span>
        </div>
        <div className="card">
          <ResponsiveContainer
            width="100%"
            height={Math.max(200, data.benchmarks.length * 22)}
          >
            <BarChart
              data={benchmarkChart.rows}
              layout="vertical"
              margin={{ top: 5, right: 30, left: 30, bottom: 5 }}
              barGap={1}
              barCategoryGap="18%"
            >
              <CartesianGrid
                horizontal={false}
                stroke="rgba(255,255,255,0.04)"
              />
              <XAxis
                type="number"
                domain={[0, 100]}
                tick={{
                  fill: "var(--text-dim)",
                  fontSize: 10,
                  fontFamily: "var(--font-mono)",
                }}
                tickFormatter={(v: number) => `${v}%`}
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                type="category"
                dataKey="benchmark"
                tick={{
                  fill: "var(--text-mid)",
                  fontSize: 10,
                  fontFamily: "var(--font-mono)",
                }}
                axisLine={false}
                tickLine={false}
                width={130}
              />
              <Tooltip
                shared={false}
                cursor={{ fill: "rgba(255,255,255,0.04)" }}
                content={({ active, payload }) => {
                  const item = payload?.[0];
                  const series = item
                    ? benchmarkChart.seriesByDataKey.get(String(item.dataKey))
                    : undefined;
                  const row = item?.payload as CompareBenchmarkRow | undefined;
                  if (!active || !series || !row) return null;
                  const values = compareBenchmarkPairValues(
                    row,
                    benchmarkChart.series,
                    series.pairId
                  );
                  return (
                    <div style={tooltipStyle}>
                      <div style={{ color: "var(--text)", marginBottom: 2 }}>
                        {row.benchmark}
                      </div>
                      <div
                        style={{ color: "var(--text-mid)", marginBottom: 4 }}
                      >
                        {series.label}
                      </div>
                      {visibleOutputModes(outputMode).map((mode) => (
                        <div key={mode} style={{ marginTop: 5 }}>
                          <span style={{ color: "var(--text-mid)" }}>
                            {outputModeLabel(mode)}:{" "}
                          </span>
                          <span style={{ color: "var(--text-dim)" }}>
                            {values[mode] == null
                              ? "No data"
                              : `${values[mode]}%`}
                          </span>
                        </div>
                      ))}
                    </div>
                  );
                }}
              />
              {benchmarkChart.series.map((series) => {
                const style = getOutputModeBarStyle(
                  series.color,
                  series.outputMode
                );
                return (
                  <Bar
                    key={series.dataKey}
                    dataKey={series.dataKey}
                    name={series.label}
                    fill={style.fill}
                    fillOpacity={style.fillOpacity}
                    stroke={style.stroke}
                    strokeWidth={style.strokeWidth}
                    barSize={outputMode === "both" ? 6 : 10}
                    isAnimationActive={false}
                  />
                );
              })}
            </BarChart>
          </ResponsiveContainer>
        </div>
        <CompareModelLegend items={compareLegendItems} />
        <OutputModeLegend outputMode={outputMode} />
      </section>

      <section className="mb-10">
        <div className="section-label">
          <span>Head-to-Head</span>
        </div>
        <ScatterPlot
          modelA={selectedModels[0]}
          modelB={selectedModels[1] || selectedModels[0]}
        />
      </section>
    </div>
  );
}
