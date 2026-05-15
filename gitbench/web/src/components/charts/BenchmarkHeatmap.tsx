import { useState, useEffect } from 'react';
import type { GitBenchData } from '@/lib/types';
import { loadData } from '@/lib/load-data';
import { modelPath } from '@/lib/routes';
import ModelSelector from './ModelSelector';
import { Badge } from '@/components/ui/badge';

function heatBg(ratio: number): string {
  if (ratio >= 0.9) return 'rgba(16,185,129,0.28)';
  if (ratio >= 0.8) return 'rgba(16,185,129,0.18)';
  if (ratio >= 0.7) return 'rgba(245,158,11,0.18)';
  if (ratio >= 0.5) return 'rgba(245,158,11,0.12)';
  return 'rgba(244,63,94,0.15)';
}

function heatColor(ratio: number): string {
  if (ratio >= 0.8) return 'var(--color-pass)';
  if (ratio >= 0.5) return 'var(--color-warn)';
  return 'var(--color-fail)';
}

export default function BenchmarkHeatmap() {
  const [data, setData] = useState<GitBenchData | null>(null);
  const [selectedModels, setSelectedModels] = useState<string[]>([]);

  useEffect(() => {
    loadData().then(d => {
      setData(d);
      setSelectedModels(d.models.map(m => m.name));
    });
  }, []);

  if (!data) return <div>Loading...</div>;

  return (
    <div>
      <ModelSelector
        initialSelected={selectedModels}
        onChange={setSelectedModels}
      />
      <div className="card overflow-x-auto p-5">
        <table className="data-table">
          <thead>
            <tr>
              <th>Benchmark</th>
              {selectedModels.map(m => (
                <th key={m}>
                  <a
                    href={modelPath(m)}
                    className="text-inherit no-underline"
                  >
                    {m}
                  </a>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.benchmarks.map(bench => (
              <tr key={bench}>
                <td className="font-mono text-xs text-[var(--color-text-mid)]">
                  <a
                    href={`/benchmarks/${bench}`}
                    className="text-inherit no-underline"
                  >
                    {bench}
                  </a>
                </td>
                {selectedModels.map(m => {
                  const cell = data.matrix[m]?.[bench];
                  if (!cell) {
                    return (
                      <td key={m}>
                        <span className="text-[var(--color-text-dim)] opacity-40 font-mono text-xs">—</span>
                      </td>
                    );
                  }
                  return (
                    <td key={m}>
                      <a
                        href={`/benchmarks/${bench}`}
                        className="no-underline"
                      >
                        <Badge
                          variant="outline"
                          className="font-mono text-xs"
                          style={{
                            background: heatBg(cell.pass_at_k),
                            color: heatColor(cell.pass_at_k),
                            borderColor: `${heatColor(cell.pass_at_k)}33`,
                          }}
                        >
                          {Math.round(cell.pass_at_k * 1000) / 10}%
                        </Badge>
                        <span className="font-mono text-[0.65rem] text-[var(--color-text-dim)] ml-1">
                          {cell.passed}/{cell.total}
                        </span>
                      </a>
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
