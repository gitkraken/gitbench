import { useState, useEffect } from 'react';
import { ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, ResponsiveContainer, Tooltip, ZAxis, ReferenceLine } from 'recharts';
import type { GitBenchData } from '@/lib/types';
import { loadData } from '@/lib/load-data';
import { modelLevelPath } from '@/lib/routes';

interface ChartPoint {
  x: number;
  y: number;
  model: string;
  provider: string;
  baseModel: string;
  level: string;
}

export default function CostValueChart() {
  const [data, setData] = useState<GitBenchData | null>(null);

  useEffect(() => {
    loadData().then(d => setData(d));
  }, []);

  if (!data) return <div class="font-mono text-xs text-[var(--color-text-dim)]">Loading chart...</div>;

  // Build chart data: include only models with valid cost data
  const chartData: ChartPoint[] = [];
  for (const m of data.models) {
    const summary = data.model_summaries[m.name];
    if (summary && summary.total_cost_usd != null && summary.pass_at_k != null) {
      chartData.push({
        x: summary.total_cost_usd,
        y: Math.round(summary.pass_at_k * 1000) / 10,
        model: m.name,
        provider: m.provider,
        baseModel: m.baseModel,
        level: m.reasoningLevel || '',
      });
    }
  }

  // Edge case: no models with cost data
  if (chartData.length === 0) {
    return (
      <div class="card p-8 text-center">
        <div class="font-display text-base text-[var(--color-text-dim)] mb-1">No pricing data available</div>
        <div class="font-mono text-xs text-[var(--color-text-dim)] opacity-60">
          Run benchmarks through OpenRouter to collect cost data for each model.
        </div>
      </div>
    );
  }

  // Compute median X and Y
  const sortedX = [...chartData].sort((a, b) => a.x - b.x);
  const sortedY = [...chartData].sort((a, b) => a.y - b.y);
  const mid = Math.floor(chartData.length / 2);
  const medianX = chartData.length % 2 === 0
    ? (sortedX[mid - 1].x + sortedX[mid].x) / 2
    : sortedX[mid].x;
  const medianY = chartData.length % 2 === 0
    ? (sortedY[mid - 1].y + sortedY[mid].y) / 2
    : sortedY[mid].y;

  // Format cost for display
  const formatCost = (v: number): string => {
    if (v < 0.0001) return `$${v.toExponential(1)}`;
    if (v < 0.01) return `$${v.toFixed(6)}`;
    return `$${v.toFixed(4)}`;
  };

  return (
    <div class="card">
      <ResponsiveContainer width="100%" height={380}>
        <ScatterChart margin={{ top: 20, right: 20, bottom: 30, left: 20 }}>
          <CartesianGrid stroke="rgba(255,255,255,0.04)" />
          <XAxis
            type="number"
            dataKey="x"
            name="Total cost"
            tick={{ fill: 'var(--text-dim)', fontSize: 11, fontFamily: 'var(--font-mono)' }}
            tickFormatter={formatCost}
            axisLine={false}
            tickLine={false}
            label={{ value: 'Total cost per full run (USD)', position: 'bottom', offset: 10, fill: 'var(--text-dim)', fontSize: 11, fontFamily: 'var(--font-mono)' }}
          />
          <YAxis
            type="number"
            dataKey="y"
            name="Pass rate"
            domain={[0, 100]}
            tick={{ fill: 'var(--text-dim)', fontSize: 11, fontFamily: 'var(--font-mono)' }}
            tickFormatter={(v: number) => `${v}%`}
            axisLine={false}
            tickLine={false}
            label={{ value: 'Pass rate', angle: -90, position: 'left', offset: 0, fill: 'var(--text-dim)', fontSize: 11, fontFamily: 'var(--font-mono)' }}
          />
          <ZAxis range={[40, 40]} />
          <ReferenceLine
            x={medianX}
            stroke="var(--color-border-accent)"
            strokeDasharray="4 4"
            strokeOpacity={0.5}
          />
          <ReferenceLine
            y={medianY}
            stroke="var(--color-border-accent)"
            strokeDasharray="4 4"
            strokeOpacity={0.5}
          />
          <Tooltip
            contentStyle={{
              background: 'var(--card)',
              border: '1px solid var(--border)',
              borderRadius: '8px',
              fontFamily: 'var(--font-mono)',
              fontSize: '0.72rem',
              color: 'var(--text)',
            }}
            formatter={(value: any, name: string) => {
              if (name === 'Total cost') return [formatCost(value), name];
              if (name === 'Pass rate') return [`${value}%`, name];
              return [value, name];
            }}
            labelFormatter={(label: any, payload: any[]) => {
              if (payload && payload[0]) return payload[0].payload.model;
              return '';
            }}
          />
          <Scatter
            data={chartData}
            fill="#a78bfa"
            shape={(props: any) => {
              const { cx, cy, payload } = props;
              const url = modelLevelPath(payload.provider, payload.baseModel, payload.level);
              return (
                <a href={url}>
                  <circle
                    cx={cx}
                    cy={cy}
                    r={5}
                    fill="#a78bfa"
                    opacity={0.75}
                    class="cursor-pointer hover:opacity-100 transition-opacity"
                  />
                </a>
              );
            }}
            isAnimationActive={false}
          />
        </ScatterChart>
      </ResponsiveContainer>
    </div>
  );
}
