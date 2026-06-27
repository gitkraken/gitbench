import { useEffect, useMemo, useState } from "react";
import {
  CartesianGrid,
  Label,
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
import { loadQuadrantChart } from "@/lib/report-client";
import { modelGroupPath } from "@/lib/routes";
import { getProviderColor } from "@/lib/provider-colors";
import ProviderIcon from "@/components/ProviderIcon";
import ModelSelector from "@/components/charts/ModelSelector";
import OutputModeSelector from "@/components/charts/OutputModeSelector";
import { useSyncedModelSelection } from "@/components/charts/useSyncedModelSelection";
import {
  costMetric,
  outputModeLabel,
  passRateMetric,
  runtimeMetric,
  tokenMetric,
  type MetricExtractor,
  type OutputMode,
  visibleOutputModes,
} from "@/components/charts/model-groups";
import {
  formatCompactDecimal,
  tooltipStyle,
  truncateName,
} from "@/components/charts/grouped-chart-ui";
import {
  buildQuadrantPoints,
  pairQuadrantPoints,
  quadrantPairForPoint,
  rankQuadrantPoints,
  type QuadrantPoint,
  type QuadrantPointPair,
} from "@/components/charts/quadrant-data";

type MetricKey = "passRate" | "cost" | "tokens" | "runtime";

interface MetricDefinition {
  key: MetricKey;
  label: string;
  shortLabel: string;
  better: "higher" | "lower";
  extractor: MetricExtractor;
  format: (value: number) => string;
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
    label: "API Time",
    shortLabel: "API Time",
    better: "lower",
    extractor: runtimeMetric,
    format: formatRuntime,
  },
];

const metricByKey = Object.fromEntries(
  METRICS.map((metric) => [metric.key, metric])
) as Record<MetricKey, MetricDefinition>;

function domainFor(values: number[]): [number, number] {
  if (values.length === 0) return [0, 1];
  const min = Math.min(...values);
  const max = Math.max(...values);
  if (min === max) return [Math.max(0, min - 1), max + 1];
  const padding = Math.max((max - min) * 0.12, Math.abs(max) * 0.04, 1e-6);
  return [Math.max(0, min - padding), max + padding];
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
      .values()
  );

  if (providers.length === 0) return null;

  return (
    <div className="mt-3 flex flex-wrap justify-center gap-x-4 gap-y-2 font-mono text-[0.625rem] text-(--text-dim)">
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

function QuadrantModeLegend({ outputMode }: { outputMode: OutputMode }) {
  if (outputMode !== "both") return null;
  return (
    <div className="mt-2 flex flex-wrap justify-center gap-x-4 gap-y-2 font-mono text-[0.625rem] text-(--text-dim)">
      <span className="inline-flex items-center gap-1.5">
        <span className="h-2.5 w-2.5 rounded-full bg-(--accent)" />
        Text
      </span>
      <span className="inline-flex items-center gap-1.5">
        <span className="h-3 w-3 rounded-full border-2 border-(--accent) bg-(--accent)/20" />
        JSON
      </span>
      <span className="inline-flex items-center gap-1.5">
        <span className="h-px w-4 bg-white/35" />
        Mode pair
      </span>
    </div>
  );
}

function QuadrantPairTooltip({
  pair,
  outputMode,
  xMetric,
  yMetric,
}: {
  pair: QuadrantPointPair;
  outputMode: OutputMode;
  xMetric: MetricDefinition;
  yMetric: MetricDefinition;
}) {
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
        <ProviderIcon provider={pair.provider} size={14} />
        {pair.provider}/{pair.baseModel}
      </div>
      {visibleOutputModes(outputMode).map((mode) => {
        const point = mode === "text" ? pair.text : pair.json;
        return (
          <div key={mode} style={{ marginTop: 7 }}>
            <div
              style={{
                color: "var(--text)",
                fontSize: 10,
                fontWeight: 700,
                letterSpacing: "0.04em",
                textTransform: "uppercase",
              }}
            >
              {outputModeLabel(mode)}
            </div>
            {point ? (
              <>
                <div style={{ color: "var(--text-dim)" }}>
                  effort: {point.reasoningLevel ?? "default"}
                </div>
                <div style={{ color: "var(--text-dim)" }}>
                  {xMetric.shortLabel}: {xMetric.format(point.xRaw)}
                </div>
                <div style={{ color: "var(--text-dim)" }}>
                  {yMetric.shortLabel}: {yMetric.format(point.yRaw)}
                </div>
              </>
            ) : (
              <div style={{ color: "var(--text-dim)" }}>No data</div>
            )}
          </div>
        );
      })}
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
    <label className="flex flex-col gap-1 text-[0.65rem] font-mono uppercase tracking-[0.08em] text-(--text-dim)">
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

function PointShape({ cx, cy, payload, onFocusPair, onBlurPair }: any) {
  if (cx == null || cy == null || !payload) return null;
  const color = getProviderColor(payload.provider);
  const isJson = payload.outputMode === "json_schema";
  const isCoincidentJson = isJson && payload.coincident;
  return (
    <g
      role="button"
      tabIndex={0}
      style={{ cursor: "pointer" }}
      aria-label={`${payload.provider}/${payload.baseModel} ${outputModeLabel(
        payload.outputMode
      )}`}
      onFocus={() => onFocusPair?.(payload.pairId)}
      onBlur={() => onBlurPair?.()}
      onClick={() => {
        window.location.href = modelGroupPath(
          payload.provider,
          payload.baseModel
        );
      }}
      onKeyDown={(event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          window.location.href = modelGroupPath(
            payload.provider,
            payload.baseModel
          );
        }
      }}
    >
      <circle
        cx={cx}
        cy={cy}
        r={isCoincidentJson ? 11 : 8}
        fill={isCoincidentJson ? "none" : color}
        fillOpacity={isJson ? 0.24 : 0.92}
        stroke={isJson ? color : "rgba(255,255,255,0.72)"}
        strokeWidth={isJson ? 2.2 : 1.5}
      />
    </g>
  );
}

import { useCampaignId } from "@/lib/use-campaign";

export default function QuadrantComparisonChart() {
  const [data, setData] = useState<GitBenchData | null>(null);
  const campaignId = useCampaignId();
  const [xMetricKey, setXMetricKey] = useState<MetricKey>("cost");
  const [yMetricKey, setYMetricKey] = useState<MetricKey>("passRate");
  const [focusedPairId, setFocusedPairId] = useState<string | null>(null);
  const {
    selectedGroups,
    setSelectedGroups,
    outputMode,
    setOutputMode,
    availableOutputModes,
  } = useSyncedModelSelection(data);

  useEffect(() => {
    loadQuadrantChart().then(setData);
  }, [campaignId]);

  const xMetric = metricByKey[xMetricKey];
  const yMetric = metricByKey[yMetricKey];

  const chartData = useMemo(() => {
    if (!data) return [];
    return buildQuadrantPoints(
      data,
      selectedGroups,
      xMetric,
      yMetric,
      outputMode
    );
  }, [data, selectedGroups, xMetric, yMetric, outputMode]);
  const pointPairs = useMemo(() => pairQuadrantPoints(chartData), [chartData]);
  const jsonPoints = useMemo(
    () =>
      pointPairs.flatMap((pair) =>
        pair.json ? [{ ...pair.json, coincident: pair.coincident }] : []
      ),
    [pointPairs]
  );
  const textPoints = useMemo(
    () =>
      pointPairs.flatMap((pair) =>
        pair.text ? [{ ...pair.text, coincident: pair.coincident }] : []
      ),
    [pointPairs]
  );
  const rankedPoints = useMemo(
    () => rankQuadrantPoints(chartData, 6),
    [chartData]
  );
  const focusedPair = useMemo(
    () => pointPairs.find((pair) => pair.id === focusedPairId),
    [pointPairs, focusedPairId]
  );

  const xDomain = useMemo(
    () => domainFor(chartData.map((point) => point.x)),
    [chartData]
  );
  const yDomain = useMemo(
    () => domainFor(chartData.map((point) => point.y)),
    [chartData]
  );
  const xMid = useMemo(() => (xDomain[0] + xDomain[1]) / 2, [xDomain]);
  const yMid = useMemo(() => (yDomain[0] + yDomain[1]) / 2, [yDomain]);
  const best = rankedPoints[0];

  if (!data) return <div>Loading...</div>;

  const xBetterIsRight = xMetric.better === "higher";
  const yBetterIsTop = yMetric.better === "higher";

  const quadrantLabels = [
    {
      x1: xMid, x2: xDomain[1], y1: yMid, y2: yDomain[1],
      labelPos: "insideTopRight" as const,
      xGood: xBetterIsRight, yGood: yBetterIsTop,
    },
    {
      x1: xDomain[0], x2: xMid, y1: yMid, y2: yDomain[1],
      labelPos: "insideTopLeft" as const,
      xGood: !xBetterIsRight, yGood: yBetterIsTop,
    },
    {
      x1: xMid, x2: xDomain[1], y1: yDomain[0], y2: yMid,
      labelPos: "insideBottomRight" as const,
      xGood: xBetterIsRight, yGood: !yBetterIsTop,
    },
    {
      x1: xDomain[0], x2: xMid, y1: yDomain[0], y2: yMid,
      labelPos: "insideBottomLeft" as const,
      xGood: !xBetterIsRight, yGood: !yBetterIsTop,
    },
  ];

  function quadrantLabelText(xGood: boolean, yGood: boolean): string {
    if (xGood && yGood) return "Better on both";
    if (!xGood && !yGood) return "Worse on both";
    if (xGood && !yGood) return `Better ${xMetric.shortLabel} / Worse ${yMetric.shortLabel}`;
    return `Worse ${xMetric.shortLabel} / Better ${yMetric.shortLabel}`;
  }

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
        <div className="min-w-0 flex items-center gap-3">
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
      </div>

      {chartData.length === 0 ? (
        <div className="card p-8 text-center">
          <div className="font-display text-base text-(--text-dim) mb-1">
            No comparable data available
          </div>
          <div className="font-mono text-xs text-(--text-dim) opacity-60">
            Choose two metrics that are present for the selected benchmark runs.
          </div>
        </div>
      ) : (
        <>
          <div className="card relative">
            <div className="mb-2 flex flex-wrap items-center justify-between gap-3 px-1">
              <div className="font-mono text-xs text-(--text-mid)">
                Optimal quadrant:{" "}
                <span className="text-(--accent)">
                  {xMetric.better === "higher" ? "higher" : "lower"}{" "}
                  {xMetric.shortLabel.toLowerCase()} +{" "}
                  {yMetric.better === "higher" ? "higher" : "lower"}{" "}
                  {yMetric.shortLabel.toLowerCase()}
                </span>
              </div>
              {best ? (
                <a
                  className="inline-flex items-center gap-1.5 font-mono text-xs text-(--text-mid) no-underline hover:text-(--accent)"
                  href={modelGroupPath(best.provider, best.baseModel)}
                >
                  <ProviderIcon provider={best.provider} size={14} />
                  Best blend: {best.baseModel} (
                  {outputModeLabel(best.outputMode)})
                </a>
              ) : null}
            </div>
            {focusedPair ? (
              <div className="absolute right-5 top-12 z-10">
                <QuadrantPairTooltip
                  pair={focusedPair}
                  outputMode={outputMode}
                  xMetric={xMetric}
                  yMetric={yMetric}
                />
              </div>
            ) : null}
            <ResponsiveContainer width="100%" height={430}>
              <ScatterChart
                margin={{ top: 18, right: 30, left: 16, bottom: 36 }}
              >
                <CartesianGrid stroke="rgba(255,255,255,0.045)" />
                {quadrantLabels.map((q, i) => {
                  const isOptimal = q.xGood && q.yGood;
                  return (
                    <ReferenceArea
                      key={i}
                      x1={q.x1}
                      x2={q.x2}
                      y1={q.y1}
                      y2={q.y2}
                      fill={isOptimal ? "var(--accent)" : "transparent"}
                      fillOpacity={isOptimal ? 0.1 : 0}
                      strokeOpacity={0}
                    >
                      <Label
                        position={q.labelPos}
                        offset={8}
                        value={quadrantLabelText(q.xGood, q.yGood)}
                        fill="var(--text-dim)"
                        fontSize={10}
                        fontFamily="var(--font-mono)"
                      />
                    </ReferenceArea>
                  );
                })}
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
                {pointPairs.map((pair) =>
                  pair.text && pair.json && !pair.coincident ? (
                    <ReferenceLine
                      key={pair.id}
                      segment={[
                        { x: pair.text.x, y: pair.text.y },
                        { x: pair.json.x, y: pair.json.y },
                      ]}
                      stroke="rgba(229,232,238,0.34)"
                      strokeWidth={1.4}
                      ifOverflow="extendDomain"
                    />
                  ) : null
                )}
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
                    const pair = point
                      ? quadrantPairForPoint(pointPairs, point)
                      : undefined;
                    if (!active || !pair) return null;
                    return (
                      <QuadrantPairTooltip
                        pair={pair}
                        outputMode={outputMode}
                        xMetric={xMetric}
                        yMetric={yMetric}
                      />
                    );
                  }}
                />
                {jsonPoints.length > 0 ? (
                  <Scatter
                    name="JSON"
                    data={jsonPoints}
                    isAnimationActive={false}
                    shape={
                      <PointShape
                        onFocusPair={setFocusedPairId}
                        onBlurPair={() => setFocusedPairId(null)}
                      />
                    }
                  />
                ) : null}
                {textPoints.length > 0 ? (
                  <Scatter
                    name="Text"
                    data={textPoints}
                    isAnimationActive={false}
                    shape={
                      <PointShape
                        onFocusPair={setFocusedPairId}
                        onBlurPair={() => setFocusedPairId(null)}
                      />
                    }
                  />
                ) : null}
              </ScatterChart>
            </ResponsiveContainer>
            <div className="mt-2 grid gap-2 border-t border-(--border) pt-3 sm:grid-cols-2 lg:grid-cols-3">
              {rankedPoints.map((point, index) => (
                <a
                  key={point.id}
                  href={modelGroupPath(point.provider, point.baseModel)}
                  className="flex min-w-0 items-center gap-2 rounded-md px-2 py-1.5 text-xs text-(--text-mid) no-underline transition hover:bg-white/3 hover:text-(--text)"
                >
                  <span className="font-mono text-(--text-dim)">
                    {index + 1}
                  </span>
                  <ProviderIcon provider={point.provider} size={14} />
                  <span className="truncate">
                    {truncateName(point.baseModel, 20)} (
                    {outputModeLabel(point.outputMode)})
                  </span>
                  <span className="ml-auto font-mono text-(--text-dim)">
                    {formatCompactDecimal(point.compositeScore * 100, 0)}
                  </span>
                </a>
              ))}
            </div>
          </div>
          <ProviderDotLegend points={chartData} />
          <QuadrantModeLegend outputMode={outputMode} />
        </>
      )}
    </div>
  );
}
