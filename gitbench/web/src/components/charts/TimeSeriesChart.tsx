import { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, ResponsiveContainer, Tooltip } from 'recharts';
import type { GitBenchData, RunMeta } from '@/lib/types';
import { loadData } from '@/lib/load-data';
import ModelSelector from './ModelSelector';
import { expandGroupSelection, groupIdsForData } from './model-groups';

const COLORS = ['#06b6d4', '#10b981', '#f59e0b', '#f43f5e', '#8b5cf6', '#ec4899', '#0ea5e9', '#84cc16'];

export default function TimeSeriesChart() {
  const [data, setData] = useState<GitBenchData | null>(null);
  const [selectedGroups, setSelectedGroups] = useState<string[]>([]);

  useEffect(() => {
    loadData().then(d => {
      setData(d);
      setSelectedGroups(groupIdsForData(d));
    });
  }, []);

  if (!data) return <div>Loading...</div>;

  const selectedModels = expandGroupSelection(selectedGroups, data);

  const runsByModel: Record<string, RunMeta[]> = {};
  for (const run of data.runs_meta) {
    if (!runsByModel[run.model]) runsByModel[run.model] = [];
    runsByModel[run.model].push(run);
  }

  const dateSet = new Set<string>();
  for (const runs of Object.values(runsByModel)) {
    for (const r of runs) {
      const date = r.timestamp.split('T')[0];
      dateSet.add(date);
    }
  }

  const sortedDates = Array.from(dateSet).sort();

  const chartData = sortedDates.map(date => {
    const point: Record<string, string | number> = { date };
    for (const model of selectedModels) {
      const runs = runsByModel[model] || [];
      const runOnDate = runs.find(r => r.timestamp.startsWith(date));
      if (runOnDate) {
        const summary = data.model_summaries[model];
        point[model] = summary ? Math.round(summary.pass_at_k * 1000) / 10 : 0;
      }
    }
    return point;
  });

  return (
    <div>
      <div className="max-w-xs ml-auto w-full mb-3">
        <ModelSelector
          value={selectedGroups}
          onChange={setSelectedGroups}
        />
      </div>
      <div className="card" title="Pass rate over calendar time. Each point = a benchmark run on that date. Changes may reflect model updates or benchmark suite changes.">
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={chartData} margin={{ top: 5, right: 30, left: 10, bottom: 5 }}>
            <CartesianGrid stroke="rgba(255,255,255,0.04)" />
            <XAxis
              dataKey="date"
              tick={{ fill: 'var(--text-dim)', fontSize: 11, fontFamily: 'var(--font-mono)' }}
              axisLine={false}
              tickLine={false}
            />
            <YAxis
              domain={[0, 100]}
              tick={{ fill: 'var(--text-dim)', fontSize: 11, fontFamily: 'var(--font-mono)' }}
              tickFormatter={(v: number) => `${v}%`}
              axisLine={false}
              tickLine={false}
            />
            <Tooltip
              content={({ active, payload, label }) => {
                if (!active || !payload || !payload.length) return null;
                return (
                  <div style={{
                    background: 'var(--card)',
                    border: '1px solid var(--border)',
                    borderRadius: '8px',
                    padding: '8px 12px',
                    fontFamily: 'var(--font-mono)',
                    fontSize: '0.75rem',
                    color: 'var(--text)',
                  }}>
                    <div style={{ marginBottom: 4, color: 'var(--text-dim)', fontSize: '0.7rem' }}>
                      {label}
                    </div>
                    {payload.map((p: any) => (
                      <div key={p.dataKey} style={{ color: p.color, marginBottom: 1 }}>
                        {p.dataKey}: {p.value}%
                      </div>
                    ))}
                    <div style={{ borderTop: '1px solid rgba(255,255,255,0.06)', margin: '6px 0' }} />
                    <div style={{ color: 'var(--text-dim)', fontSize: 10, lineHeight: 1.4 }}>
                      Pass rate on this date. Changes may reflect<br/>
                      model updates or benchmark suite changes.
                    </div>
                  </div>
                );
              }}
            />
            {selectedModels.map((model, i) => (
              <Line
                key={model}
                type="monotone"
                dataKey={model}
                stroke={COLORS[i % COLORS.length]}
                strokeWidth={2}
                dot={{ r: 3 }}
                connectNulls
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
