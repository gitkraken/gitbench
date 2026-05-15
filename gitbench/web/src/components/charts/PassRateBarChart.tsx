import { useState, useEffect } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, ResponsiveContainer, Cell } from 'recharts';
import type { GitBenchData } from '@/lib/types';
import { loadData } from '@/lib/load-data';
import ModelSelector from './ModelSelector';
import ProviderIcon from '@/components/ProviderIcon';

function getColor(passRate: number): string {
  if (passRate >= 0.8) return 'var(--pass)';
  if (passRate >= 0.5) return 'var(--warn)';
  return 'var(--fail)';
}

/** Truncate a model name for display, preserving end characters. */
function truncateName(name: string, maxLen = 10): string {
  if (name.length <= maxLen) return name;
  return name.slice(0, maxLen - 1) + '…';
}

interface TickPayload {
  x: number;
  y: number;
  payload: {
    name: string;
    provider: string;
    baseModel: string;
    reasoningLevel: string | null;
    passRate: number;
    raw: number;
  };
}

function CustomXAxisTick(props: TickPayload) {
  const { x, y, payload } = props;
  const baseName = truncateName(payload.baseModel);

  return (
    <g transform={`translate(${x},${y})`}>
      <g transform="rotate(-40)">
        {/* Provider icon + model name + level */}
        <foreignObject
          x={-60}
          y={-12}
          width={120}
          height={32}
          style={{ overflow: 'visible' }}
        >
          <div
            style={{
              display: 'flex',
              flexDirection: 'row',
              alignItems: 'center',
              gap: 3,
              fontSize: 9,
              fontFamily: 'var(--font-mono)',
              color: 'var(--text-mid)',
              whiteSpace: 'nowrap',
              justifyContent: 'center',
            }}
          >
            <ProviderIcon provider={payload.provider} size={12} />
            <span>{baseName}</span>
            {payload.reasoningLevel && (
              <span style={{ color: 'var(--text-dim)', fontSize: 8 }}>
                {payload.reasoningLevel}
              </span>
            )}
          </div>
        </foreignObject>
      </g>
    </g>
  );
}

export default function PassRateBarChart() {
  const [data, setData] = useState<GitBenchData | null>(null);
  const [selectedModels, setSelectedModels] = useState<string[]>([]);

  useEffect(() => {
    loadData().then(d => {
      setData(d);
      setSelectedModels(d.models.map(m => m.name));
    });
  }, []);

  if (!data) return <div>Loading...</div>;

  const chartData = selectedModels
    .map(name => {
      const summary = data.model_summaries[name];
      const info = data.models.find(m => m.name === name);
      if (!summary) return null;
      return {
        name,
        provider: info?.provider || '',
        baseModel: info?.baseModel || name,
        reasoningLevel: info?.reasoningLevel,
        passRate: Math.round(summary.pass_at_k * 1000) / 10,
        raw: summary.pass_at_k,
      };
    })
    .filter((d): d is NonNullable<typeof d> => d !== null)
    .sort((a, b) => b.passRate - a.passRate);

  const chartHeight = Math.max(300, chartData.length * 80);
  const bottomMargin = 80; // room for -40° rotated labels

  return (
    <div>
      <div className="max-w-xs ml-auto w-full mb-3">
        <ModelSelector
          initialSelected={selectedModels}
          onChange={setSelectedModels}
        />
      </div>
      <div className="card">
        <ResponsiveContainer width="100%" height={chartHeight}>
          <BarChart
            data={chartData}
            layout="horizontal"
            margin={{ top: 5, right: 20, left: 0, bottom: bottomMargin }}
          >
            <CartesianGrid vertical={false} stroke="rgba(255,255,255,0.04)" />
            <XAxis
              type="category"
              dataKey="name"
              tick={(props: any) => <CustomXAxisTick {...props} />}
              axisLine={false}
              tickLine={false}
              interval={0}
              height={bottomMargin}
            />
            <YAxis
              type="number"
              domain={[0, 100]}
              tick={{ fill: 'var(--text-dim)', fontSize: 11, fontFamily: 'var(--font-mono)' }}
              tickFormatter={(v: number) => `${v}%`}
              axisLine={false}
              tickLine={false}
            />
            <Bar dataKey="passRate" radius={[4, 4, 0, 0]} barSize={Math.max(12, Math.min(28, 400 / Math.max(1, chartData.length)))}>
              {chartData.map((entry, index) => (
                <Cell key={index} fill={getColor(entry.raw)} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
