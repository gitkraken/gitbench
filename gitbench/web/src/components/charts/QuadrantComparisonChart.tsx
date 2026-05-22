import { useEffect, useMemo, useState } from "react";
import {
  CartesianGrid,
  ReferenceArea,
  ReferenceLine,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
  ZAxis,
} from "recharts";
import type { GitBenchData } from "@/lib/types";
import { loadData } from "@/lib/load-data";
import { modelGroupPath } from "@/lib/routes";
import { getProviderColor } from "@/lib/provider-colors";
import ProviderIcon from "@/components/ProviderIcon";
import ModelSelector from "@/components/charts/ModelSelector";
import { useSyncedModelSelection } from "@/components/charts/useSyncedModelSelection";
import {
  costMetric,
  deriveModelGroups,
  passRateMetric,
  runtimeMetric,
  sanitizeGroupSelection,
  tokenMetric,
  type MetricEffort,
  type MetricExtractor,
  type ModelGroup,
} from "@/components/charts/model-groups";
import {
  formatCompactDecimal,
  tooltipStyle,
  truncateName,
} from "@/components/charts/grouped-chart-ui";

type MetricKey = "passRate" | "cost" | "tokens" | "runtime";

interface MetricDefinition {
  key: MetricKey;
  label: string;
  shortLabel: string;
  better: "higher" | "lower";
  extractor: MetricExtractor;
  format: (value: number) => string;
}

interface QuadrantPoint {
  id: string;
  provider: string;
  baseModel: string;
  modelName: string;
  reasoningLevel: string | null;
  x: number;
  y: number;
  xRaw: number;
  yRaw: number;
  xScore: number;
  yScore: number;
  compositeScore: number;
}

function formatCost(value: number): string {
  if (value < 0.0001) return `$${value.toExponential(1)}`;
  if (value < 0.01) return `$${formatCompactDecimal(value, 3)}`;
  return `$${formatCompactDecimal(value, 2)}`;
}

function formatTokens(value: number): string {
  if (value >= 1_000_000)
    return `${formatCompactDecimal(value / 1_000_000, 2)}M`;
  if (value >= 1_000) return `${formatCompactDecimal(value / 1_000, 2)}K`;
  return formatCompactDecimal(value, 0);
}

function formatRuntime(seconds: number): string {
  if (seconds >= 60) return `${formatCompactDecimal(seconds / 60, 2)}m`;
  return `${formatCompactDecimal(seconds, 2)}s`;
}

const METRICS: MetricDefinition[] = [
  {
    key: "passRate",
    label: "Intelligence (Pass Rate)",
    shortLabel: "Pass Rate",
    better: "higher",
    extractor: passRateMetric,
    format: (value) => `${formatCompactDecimal(value, 1)}%`,
  },
  {
    key: "cost",
    label: "Cost",
    shortLabel: "Cost",
    better: "lower",
    extractor: costMetric,
    format: formatCost,
  },
  {
    key: "tokens",
    label: "Token Usage",
    shortLabel: "Tokens",
    better: "lower",
    extractor: tokenMetric,
    format: formatTokens,
  },
  {
    key: "runtime",
    label: "Runtime",
    shortLabel: "Runtime",
    better: "lower",
    extractor: runtimeMetric,
    format: formatRuntime,
  },
];

const metricByKey = Object.fromEntries(
  METRICS.map((metric) => [metric.key, metric]),
) as Record<MetricKey, MetricDefinition>;

function normalize(
  value: number,
  min: number,
  max: number,
  better: MetricDefinition["better"],
) {
  if (max === min) return 0.5;
  const ratio = (value - min) / (max - min);
  return better === "higher" ? ratio : 1 - ratio;
}

function domainFor(values: number[]): [number, number] {
  if (values.length === 0) return [0, 1];
  const min = Math.min(...values);
  const max = Math.max(...values);
  if (min === max) return [Math.max(0, min - 1), max + 1];
  const padding = Math.max((max - min) * 0.12, Math.abs(max) * 0.04, 1e-6);
  return [Math.max(0, min - padding), max + padding];
}

function metricValueForGroup(
  group: ModelGroup,
  data: GitBenchData,
  metric: MetricDefinition,
): MetricEffort[] {
  return group.efforts
    .map((effort) => metric.extractor(effort, data))
    .filter((effort): effort is MetricEffort => effort !== null);
}

function buildPoints(
  data: GitBenchData,
  selectedGroups: string[],
  xMetric: MetricDefinition,
  yMetric: MetricDefinition,
): QuadrantPoint[] {
  const groups = deriveModelGroups(data);
  const selected = new Set(sanitizeGroupSelection(selectedGroups, groups));
  const candidates = groups
    .filter((group) => selected.has(group.id))
    .map((group) => {
      const xByModel = new Map(
        metricValueForGroup(group, data, xMetric).map((effort) => [
          effort.modelName,
          effort,
        ]),
      );
      const yByModel = new Map(
        metricValueForGroup(group, data, yMetric).map((effort) => [
          effort.modelName,
          effort,
        ]),
      );

      return group.efforts
        .map((effort) => {
          const x = xByModel.get(effort.modelName);
          const y = yByModel.get(effort.modelName);
          if (!x || !y) return null;
          return {
            id: group.id,
            provider: group.provider,
            baseModel: group.baseModel,
            modelName: effort.modelName,
            reasoningLevel: effort.reasoningLevel,
            xRaw: x.value,
            yRaw: y.value,
          };
        })
        .filter(
          (
            point,
          ): point is Omit<
            QuadrantPoint,
            "x" | "y" | "xScore" | "yScore" | "compositeScore"
          > => point !== null,
        );
    })
    .flat();

  if (candidates.length === 0) return [];

  const xValues = candidates.map((point) => point.xRaw);
  const yValues = candidates.map((point) => point.yRaw);
  const xMin = Math.min(...xValues);
  const xMax = Math.max(...xValues);
  const yMin = Math.min(...yValues);
  const yMax = Math.max(...yValues);

  const bestByGroup = new Map<string, QuadrantPoint>();
  for (const candidate of candidates) {
    const xScore = normalize(candidate.xRaw, xMin, xMax, xMetric.better);
    const yScore = normalize(candidate.yRaw, yMin, yMax, yMetric.better);
    const point = {
      ...candidate,
      x: candidate.xRaw,
      y: candidate.yRaw,
      xScore,
      yScore,
      compositeScore: (xScore + yScore) / 2,
    };
    const previous = bestByGroup.get(point.id);
    if (!previous || point.compositeScore > previous.compositeScore) {
      bestByGroup.set(point.id, point);
    }
  }

  return Array.from(bestByGroup.values()).sort(
    (a, b) => b.compositeScore - a.compositeScore,
  );
}

function ProviderDotLegend({ points }: { points: QuadrantPoint[] }) {
  const providers = Array.from(
    points
      .reduce((seen, point) => {
        if (!seen.has(point.provider.toLowerCase())) {
          seen.set(point.provider.toLowerCase(), point.provider);
        }
        return seen;
      }, new Map<string, string>())
      .values(),
  );

  if (providers.length === 0) return null;

  return (
    <div className="mt-3 flex flex-wrap justify-center gap-x-4 gap-y-2 font-mono text-[0.625rem] text-[var(--text-dim)]">
      {providers.map((provider) => (
        <span key={provider} className="inline-flex items-center gap-1.5">
          <span
            className="h-2 w-2 rounded-full"
            style={{ backgroundColor: getProviderColor(provider) }}
          />
          {provider}
        </span>
      ))}
    </div>
  );
}

function MetricSelect({
  label,
  value,
  onChange,
  exclude,
}: {
  label: string;
  value: MetricKey;
  onChange: (value: MetricKey) => void;
  exclude: MetricKey;
}) {
  return (
    <label className="flex flex-col gap-1 text-[0.65rem] font-mono uppercase tracking-[0.08em] text-[var(--text-dim)]">
      {label}
      <select
        className="brand-select w-full normal-case"
        value={value}
        onChange={(event) => onChange(event.target.value as MetricKey)}
      >
        {METRICS.map((metric) => (
          <option
            key={metric.key}
            value={metric.key}
            disabled={metric.key === exclude}
          >
            {metric.label}
          </option>
        ))}
      </select>
    </label>
  );
}

function PointShape(props: any) {
  const { cx, cy, payload } = props;
  if (cx == null || cy == null || !payload) return null;
  return (
    <g
      role="button"
      tabIndex={0}
      style={{ cursor: "pointer" }}
      onClick={() => {
        window.location.href = modelGroupPath(
          payload.provider,
          payload.baseModel,
        );
      }}
      onKeyDown={(event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          window.location.href = modelGroupPath(
            payload.provider,
            payload.baseModel,
          );
        }
      }}
    >
      <circle
        cx={cx}
        cy={cy}
        r={8}
        fill={getProviderColor(payload.provider)}
        fillOpacity={0.92}
        stroke="rgba(255,255,255,0.72)"
        strokeWidth={1.5}
      />
    </g>
  );
}

export default function QuadrantComparisonChart() {
  const [data, setData] = useState<GitBenchData | null>(null);
  const [xMetricKey, setXMetricKey] = useState<MetricKey>("cost");
  const [yMetricKey, setYMetricKey] = useState<MetricKey>("passRate");
  const { selectedGroups, setSelectedGroups } = useSyncedModelSelection(data);

  useEffect(() => {
    loadData().then(setData);
  }, []);

  const xMetric = metricByKey[xMetricKey];
  const yMetric = metricByKey[yMetricKey];

  const chartData = useMemo(() => {
    if (!data) return [];
    return buildPoints(data, selectedGroups, xMetric, yMetric);
  }, [data, selectedGroups, xMetric, yMetric]);

  const xDomain = useMemo(
    () => domainFor(chartData.map((point) => point.x)),
    [chartData],
  );
  const yDomain = useMemo(
    () => domainFor(chartData.map((point) => point.y)),
    [chartData],
  );
  const xMid = useMemo(() => (xDomain[0] + xDomain[1]) / 2, [xDomain]);
  const yMid = useMemo(() => (yDomain[0] + yDomain[1]) / 2, [yDomain]);
  const best = chartData[0];

  if (!data) return <div>Loading...</div>;

  const xOptimal: { x1?: number; x2?: number } =
    xMetric.better === "higher"
      ? { x1: xMid, x2: xDomain[1] }
      : { x1: xDomain[0], x2: xMid };
  const yOptimal: { y1?: number; y2?: number } =
    yMetric.better === "higher"
      ? { y1: yMid, y2: yDomain[1] }
      : { y1: yDomain[0], y2: yMid };

  return (
    <div>
      <div className="mb-3 grid gap-3 lg:grid-cols-[1fr_1fr_minmax(16rem,24rem)] items-end">
        <MetricSelect
          label="X axis"
          value={xMetricKey}
          onChange={(value) => {
            if (value !== yMetricKey) setXMetricKey(value);
          }}
          exclude={yMetricKey}
        />
        <MetricSelect
          label="Y axis"
          value={yMetricKey}
          onChange={(value) => {
            if (value !== xMetricKey) setYMetricKey(value);
          }}
          exclude={xMetricKey}
        />
        <div className="min-w-0">
          <ModelSelector value={selectedGroups} onChange={setSelectedGroups} />
        </div>
      </div>

      {chartData.length === 0 ? (
        <div className="card p-8 text-center">
          <div className="font-display text-base text-[var(--text-dim)] mb-1">
            No comparable data available
          </div>
          <div className="font-mono text-xs text-[var(--text-dim)] opacity-60">
            Choose two metrics that are present for the selected benchmark runs.
          </div>
        </div>
      ) : (
        <>
          <div className="card">
            <div className="mb-2 flex flex-wrap items-center justify-between gap-3 px-1">
              <div className="font-mono text-xs text-[var(--text-mid)]">
                Optimal quadrant:{" "}
                <span className="text-[var(--accent)]">
                  {xMetric.better === "higher" ? "higher" : "lower"}{" "}
                  {xMetric.shortLabel.toLowerCase()} +{" "}
                  {yMetric.better === "higher" ? "higher" : "lower"}{" "}
                  {yMetric.shortLabel.toLowerCase()}
                </span>
              </div>
              {best ? (
                <a
                  className="inline-flex items-center gap-1.5 font-mono text-xs text-[var(--text-mid)] no-underline hover:text-[var(--accent)]"
                  href={modelGroupPath(best.provider, best.baseModel)}
                >
                  <ProviderIcon provider={best.provider} size={14} />
                  Best blend: {best.baseModel}
                </a>
              ) : null}
            </div>
            <ResponsiveContainer width="100%" height={430}>
              <ScatterChart
                margin={{ top: 18, right: 30, left: 16, bottom: 36 }}
              >
                <CartesianGrid stroke="rgba(255,255,255,0.045)" />
                <ReferenceArea
                  {...xOptimal}
                  {...yOptimal}
                  fill="var(--accent)"
                  fillOpacity={0.1}
                  strokeOpacity={0}
                />
                <ReferenceLine
                  x={xMid}
                  stroke="rgba(255,255,255,0.16)"
                  strokeDasharray="4 4"
                />
                <ReferenceLine
                  y={yMid}
                  stroke="rgba(255,255,255,0.16)"
                  strokeDasharray="4 4"
                />
                <XAxis
                  type="number"
                  dataKey="x"
                  name={xMetric.label}
                  domain={xDomain}
                  tick={{
                    fill: "var(--text-dim)",
                    fontSize: 11,
                    fontFamily: "var(--font-mono)",
                  }}
                  tickFormatter={xMetric.format}
                  axisLine={{ stroke: "rgba(255,255,255,0.12)" }}
                  tickLine={false}
                  label={{
                    value: xMetric.label,
                    position: "insideBottom",
                    dy: 28,
                    fill: "var(--text-mid)",
                    fontSize: 11,
                    fontFamily: "var(--font-mono)",
                  }}
                />
                <YAxis
                  type="number"
                  dataKey="y"
                  name={yMetric.label}
                  domain={yDomain}
                  tick={{
                    fill: "var(--text-dim)",
                    fontSize: 11,
                    fontFamily: "var(--font-mono)",
                  }}
                  tickFormatter={yMetric.format}
                  axisLine={{ stroke: "rgba(255,255,255,0.12)" }}
                  tickLine={false}
                  width={72}
                  label={{
                    value: yMetric.label,
                    angle: -90,
                    position: "insideLeft",
                    fill: "var(--text-mid)",
                    fontSize: 11,
                    fontFamily: "var(--font-mono)",
                  }}
                />
                <ZAxis range={[80, 80]} />
                <Tooltip
                  cursor={{
                    stroke: "rgba(255,255,255,0.18)",
                    strokeDasharray: "3 3",
                  }}
                  content={({ active, payload }) => {
                    const point = payload?.[0]?.payload as
                      | QuadrantPoint
                      | undefined;
                    if (!active || !point) return null;
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
                          <ProviderIcon provider={point.provider} size={14} />
                          {point.provider}/{point.baseModel}
                        </div>
                        <div style={{ color: "var(--text-dim)" }}>
                          effort: {point.reasoningLevel ?? "default"}
                        </div>
                        <div style={{ color: "var(--text-dim)" }}>
                          {xMetric.shortLabel}: {xMetric.format(point.x)}
                        </div>
                        <div style={{ color: "var(--text-dim)" }}>
                          {yMetric.shortLabel}: {yMetric.format(point.y)}
                        </div>
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
                          Composite fit:{" "}
                          {formatCompactDecimal(point.compositeScore * 100, 1)}
                          %. Click to open the model page.
                        </div>
                      </div>
                    );
                  }}
                />
                <Scatter data={chartData} shape={<PointShape />} />
              </ScatterChart>
            </ResponsiveContainer>
            <div className="mt-2 grid gap-2 border-t border-[var(--border)] pt-3 sm:grid-cols-2 lg:grid-cols-3">
              {chartData.slice(0, 6).map((point, index) => (
                <a
                  key={point.id}
                  href={modelGroupPath(point.provider, point.baseModel)}
                  className="flex min-w-0 items-center gap-2 rounded-md px-2 py-1.5 text-xs text-[var(--text-mid)] no-underline transition hover:bg-white/[0.03] hover:text-[var(--text)]"
                >
                  <span className="font-mono text-[var(--text-dim)]">
                    {index + 1}
                  </span>
                  <ProviderIcon provider={point.provider} size={14} />
                  <span className="truncate">
                    {truncateName(point.baseModel, 24)}
                  </span>
                  <span className="ml-auto font-mono text-[var(--text-dim)]">
                    {formatCompactDecimal(point.compositeScore * 100, 0)}
                  </span>
                </a>
              ))}
            </div>
          </div>
          <ProviderDotLegend points={chartData} />
        </>
      )}
    </div>
  );
}
