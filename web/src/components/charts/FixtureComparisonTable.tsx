import { useEffect, useMemo, useState } from "react";
import type { GitBenchData } from "@/lib/types";
import { loadData } from "@/lib/load-data";
import type { BenchmarkDetail } from "@/lib/report-store";
import { loadBenchmark } from "@/lib/report-client";
import ModelOutputControls from "@/components/charts/ModelOutputControls";
import { useSyncedModelSelection } from "@/components/charts/useSyncedModelSelection";
import { deriveModelGroups } from "@/components/charts/model-groups";
import { Badge } from "@/components/ui/badge";

interface EffortColumn {
  modelName: string;
  provider: string;
  baseModel: string;
  reasoningLevel: string | null;
}

interface ColumnGroup {
  provider: string;
  baseModel: string;
  colSpan: number;
}

interface FixtureComparisonTableProps {
  benchName: string;
}

const LEVEL_ORDER = ["none", "low", "medium", "high", "xhigh", "max"];

function sortByReasoningLevel<T extends { reasoningLevel: string | null }>(
  efforts: T[]
): T[] {
  return [...efforts].sort((a, b) => {
    const ai = LEVEL_ORDER.indexOf(a.reasoningLevel ?? "none");
    const bi = LEVEL_ORDER.indexOf(b.reasoningLevel ?? "none");
    return ai - bi;
  });
}

export default function FixtureComparisonTable({
  benchName,
}: FixtureComparisonTableProps) {
  const [data, setData] = useState<GitBenchData | null>(null);
  const [benchmarkData, setBenchmarkData] = useState<BenchmarkDetail | null>(
    null
  );
  const {
    selectedGroups,
    setSelectedGroups,
    outputMode,
    setOutputMode,
    availableOutputModes,
  } = useSyncedModelSelection(data);

  useEffect(() => {
    Promise.all([loadData(), loadBenchmark(benchName)]).then(
      ([summary, benchmark]) => {
        setData(summary);
        setBenchmarkData(benchmark);
      }
    );
  }, [benchName]);

  // Build ordered list of model->effort columns from selected groups
  const allEfforts = useMemo((): EffortColumn[] => {
    if (!data) return [];
    const groups = deriveModelGroups(data).filter((g) =>
      selectedGroups.includes(g.id)
    );
    const result: EffortColumn[] = [];
    for (const group of groups) {
      const filteredEfforts =
        outputMode === "both"
          ? group.efforts
          : group.efforts.filter((e) => e.outputMode === outputMode);
      const sorted = sortByReasoningLevel(filteredEfforts);
      for (const effort of sorted) {
        result.push({
          modelName: effort.modelName,
          provider: group.provider,
          baseModel: group.baseModel,
          reasoningLevel: effort.reasoningLevel,
        });
      }
    }
    return result;
  }, [data, selectedGroups, outputMode]);

  // Group consecutive efforts with the same base model for colspan headers
  const columnGroups = useMemo((): ColumnGroup[] => {
    const groups: ColumnGroup[] = [];
    for (const e of allEfforts) {
      const key = `${e.provider}/${e.baseModel}`;
      const last = groups[groups.length - 1];
      if (last && `${last.provider}/${last.baseModel}` === key) {
        last.colSpan++;
      } else {
        groups.push({
          provider: e.provider,
          baseModel: e.baseModel,
          colSpan: 1,
        });
      }
    }
    return groups;
  }, [allEfforts]);

  // Fixture entries for this benchmark, sorted
  const fixtures = useMemo(() => {
    if (!benchmarkData) return [];
    return Object.entries(benchmarkData.fixtures)
      .filter(([, fi]) => fi.benchmark === benchName)
      .sort(([a], [b]) => a.localeCompare(b));
  }, [benchmarkData, benchName]);

  if (!data || !benchmarkData) return <div>Loading...</div>;

  return (
    <div>
      <ModelOutputControls
        data={data}
        selectedGroups={selectedGroups}
        onSelectedGroupsChange={setSelectedGroups}
        outputMode={outputMode}
        onOutputModeChange={setOutputMode}
        availableOutputModes={availableOutputModes}
      />
      <div className="card overflow-x-auto p-5">
        <table className="data-table">
          <thead>
            <tr>
              <th>Fixture</th>
              <th>Difficulty</th>
              {columnGroups.map((g) => (
                <th
                  key={`${g.provider}/${g.baseModel}`}
                  colSpan={g.colSpan}
                  className="text-center font-semibold text-xs"
                >
                  {g.baseModel}
                </th>
              ))}
            </tr>
            <tr>
              <th />
              <th />
              {allEfforts.map((e) => (
                <th
                  key={e.modelName}
                  className="font-mono text-[0.62rem] text-(--color-text-dim) text-center"
                >
                  {e.reasoningLevel || "none"}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {fixtures.map(([fid, fi]) => (
              <tr key={fid}>
                <td>
                  <a
                    href={`/fixtures/${encodeURIComponent(benchName)}/${fi.id}`}
                    className="inline-flex items-center px-2 py-0.5 rounded font-mono text-xs bg-white/5 text-(--color-text-mid) border border-border no-underline"
                  >
                    {fi.id}
                  </a>
                </td>
                <td className="font-mono text-[0.68rem] text-(--color-text-dim)">
                  {fi?.difficulty || "—"}
                </td>
                {allEfforts.map((e) => {
                  const results =
                    benchmarkData.results[e.modelName]?.[benchName] || [];
                  const fr = results.find((r) => r.fixture_id === fi.id);
                  if (!fr) {
                    return (
                      <td
                        key={e.modelName}
                        className="text-(--color-text-dim) opacity-40 font-mono text-xs"
                      >
                        —
                      </td>
                    );
                  }
                  if (fr.error) {
                    return (
                      <td
                        key={e.modelName}
                        className="text-(--color-text-dim) opacity-40 font-mono text-xs"
                      >
                        —
                      </td>
                    );
                  }
                  const sim = Math.round(fr.similarity * 1000) / 10;
                  const color = fr.passed
                    ? "bg-pass-bg text-pass border-pass-border"
                    : "bg-fail-bg text-fail border-(--color-fail-border)";
                  return (
                    <td key={e.modelName}>
                      <Badge
                        variant="outline"
                        className={`font-mono text-[0.62rem] ${color}`}
                      >
                        {sim}%
                      </Badge>
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
