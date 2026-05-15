import { useState, useEffect } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, ResponsiveContainer, Cell, Legend } from 'recharts';
import type { GitBenchData } from '@/lib/types';
import { loadData } from '@/lib/load-data';
import ModelSelector from './charts/ModelSelector';
import ScatterPlot from './charts/ScatterPlot';
import { Badge } from '@/components/ui/badge';

const COLORS = ['#06b6d4', '#10b981', '#f59e0b', '#f43f5e', '#8b5cf6', '#ec4899', '#0ea5e9', '#84cc16'];

function getColor(passRate: number): string {
  if (passRate >= 0.8) return 'var(--color-pass)';
  if (passRate >= 0.5) return 'var(--color-warn)';
  return 'var(--color-fail)';
}

export default function ComparePage() {
  const [data, setData] = useState<GitBenchData | null>(null);
  const [selectedModels, setSelectedModels] = useState<string[]>([]);

  useEffect(() => {
    loadData().then(d => {
      setData(d);
      const params = new URLSearchParams(window.location.search);
      const withModel = params.get('with');
      const initial = withModel ? [withModel] : d.models.slice(0, 3).map(m => m.name);
      setSelectedModels(initial);
    });
  }, []);

  if (!data) return <div>Loading...</div>;

  const overallData = selectedModels
    .map(name => {
      const summary = data.model_summaries[name];
      if (!summary) return null;
      return {
        name,
        passRate: Math.round(summary.pass_at_k * 1000) / 10,
        raw: summary.pass_at_k,
      };
    })
    .filter((d): d is NonNullable<typeof d> => d !== null)
    .sort((a, b) => b.passRate - a.passRate);

  const byBenchData = data.benchmarks.map(bench => {
    const row: Record<string, string | number> = { benchmark: bench };
    for (const model of selectedModels) {
      const cell = data.matrix[model]?.[bench];
      row[model] = cell ? Math.round(cell.pass_at_k * 1000) / 10 : 0;
    }
    return row;
  });

  return (
    <div>
      <div className="max-w-xs ml-auto w-full mb-6">
        <ModelSelector
          initialSelected={selectedModels}
          onChange={setSelectedModels}
        />
      </div>

      <section className="mb-10">
        <div className="section-label"><span>Overall Pass Rates</span></div>
        <div className="card">
          <ResponsiveContainer width="100%" height={Math.max(180, selectedModels.length * 36)}>
            <BarChart
              data={overallData}
              layout="vertical"
              margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
            >
              <CartesianGrid horizontal={false} stroke="rgba(255,255,255,0.04)" />
              <XAxis
                type="number"
                domain={[0, 100]}
                tick={{ fill: 'var(--text-dim)', fontSize: 11, fontFamily: 'var(--font-mono)' }}
                tickFormatter={(v: number) => `${v}%`}
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                type="category"
                dataKey="name"
                tick={{ fill: 'var(--text-mid)', fontSize: 11, fontFamily: 'var(--font-mono)' }}
                axisLine={false}
                tickLine={false}
                width={140}
              />
              <Bar dataKey="passRate" radius={[0, 4, 4, 0]} barSize={16}>
                {overallData.map((entry, index) => (
                  <Cell key={index} fill={getColor(entry.raw)} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </section>

      <section className="mb-10">
        <div className="section-label"><span>By Benchmark</span></div>
        <div className="card">
          <ResponsiveContainer width="100%" height={Math.max(200, data.benchmarks.length * 22)}>
            <BarChart
              data={byBenchData}
              layout="vertical"
              margin={{ top: 5, right: 30, left: 30, bottom: 5 }}
            >
              <CartesianGrid horizontal={false} stroke="rgba(255,255,255,0.04)" />
              <XAxis
                type="number"
                domain={[0, 100]}
                tick={{ fill: 'var(--text-dim)', fontSize: 10, fontFamily: 'var(--font-mono)' }}
                tickFormatter={(v: number) => `${v}%`}
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                type="category"
                dataKey="benchmark"
                tick={{ fill: 'var(--text-mid)', fontSize: 10, fontFamily: 'var(--font-mono)' }}
                axisLine={false}
                tickLine={false}
                width={130}
              />
              <Legend
                wrapperStyle={{ fontFamily: 'var(--font-mono)', fontSize: '0.65rem', color: 'var(--text-dim)' }}
              />
              {selectedModels.map((model, i) => (
                <Bar key={model} dataKey={model} fill={COLORS[i % COLORS.length]} radius={[0, 2, 2, 0]} barSize={10} />
              ))}
            </BarChart>
          </ResponsiveContainer>
        </div>
      </section>

      <section className="mb-10">
        <div className="section-label"><span>Head-to-Head</span></div>
        <ScatterPlot
          modelA={selectedModels[0]}
          modelB={selectedModels[1] || selectedModels[0]}
        />
      </section>
    </div>
  );
}
