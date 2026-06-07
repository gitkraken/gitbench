import { useState, useEffect } from "react";
import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  ZAxis,
} from "recharts";
import type { GitBenchData } from "@/lib/types";
import { loadData } from "@/lib/load-data";
import { loadModelResults } from "@/lib/report-client";
import { Badge } from "@/components/ui/badge";
import {
  deriveModelGroups,
  outputModeLabel,
  splitModelVariantKey,
} from "@/components/charts/model-groups";

interface Props {
  modelA?: string;
  modelB?: string;
}

function dotColor(aPassed: boolean, bPassed: boolean): string {
  if (aPassed && bPassed) return "#097886";
  if (!aPassed && !bPassed) return "#CE5478";
  return "#FEDC00";
}

export default function ScatterPlot({ modelA, modelB }: Props) {
  const [data, setData] = useState<GitBenchData | null>(null);
  const [modelResults, setModelResults] = useState<
    Record<string, Awaited<ReturnType<typeof loadModelResults>>["results"]>
  >({});
  const [a, setA] = useState(modelA || "");
  const [b, setB] = useState(modelB || "");

  useEffect(() => {
    loadData().then((d) => {
      setData(d);
      const modelNames = deriveModelGroups(d).flatMap((group) =>
        group.efforts.map((effort) => effort.modelName)
      );
      if (!modelA) setA(modelNames[0] || "");
      if (!modelB) setB(modelNames[1] || modelNames[0] || "");
    });
  }, []);

  useEffect(() => {
    const models = [a, b].filter(Boolean);
    const missing = models.filter((model) => !modelResults[model]);
    if (missing.length === 0) return;

    Promise.all(missing.map((model) => loadModelResults(model))).then(
      (responses) => {
        setModelResults((current) => {
          const next = { ...current };
          for (const response of responses) {
            next[response.model] = response.results;
          }
          return next;
        });
      }
    );
  }, [a, b, modelResults]);

  if (!data || !a || !b || !modelResults[a] || !modelResults[b]) {
    return <div>Loading...</div>;
  }

  const aFixtures = modelResults[a] || {};
  const bFixtures = modelResults[b] || {};

  const scatterData: {
    x: number;
    y: number;
    fixture: string;
    aPassed: boolean;
    bPassed: boolean;
  }[] = [];

  for (const bench of data.benchmarks) {
    const aResults = aFixtures[bench] || [];
    const bResults = bFixtures[bench] || [];
    for (const ar of aResults) {
      const br = bResults.find((r) => r.fixture_id === ar.fixture_id);
      if (br) {
        scatterData.push({
          x: Math.round(ar.similarity * 1000) / 10,
          y: Math.round(br.similarity * 1000) / 10,
          fixture: `${bench}/${ar.fixture_id}`,
          aPassed: ar.passed,
          bPassed: br.passed,
        });
      }
    }
  }

  let bothPass = 0,
    bothFail = 0,
    aOnly = 0,
    bOnly = 0;
  for (const d of scatterData) {
    if (d.aPassed && d.bPassed) bothPass++;
    else if (!d.aPassed && !d.bPassed) bothFail++;
    else if (d.aPassed) aOnly++;
    else bOnly++;
  }

  const modelNames = deriveModelGroups(data).flatMap((group) =>
    group.efforts.map((effort) => effort.modelName)
  );
  const modelLabel = (modelName: string) => {
    const variant = splitModelVariantKey(modelName);
    return `${variant.canonicalModelName} (${outputModeLabel(
      variant.outputMode
    )})`;
  };

  return (
    <div>
      <div className="flex gap-4 mb-4 flex-wrap items-center">
        <label className="font-mono text-xs text-(--color-text-dim)">
          X:{" "}
          <select
            value={a}
            onChange={(e) => setA(e.target.value)}
            className="brand-select w-full text-xs"
          >
            {modelNames.map((m) => (
              <option key={m} value={m}>
                {modelLabel(m)}
              </option>
            ))}
          </select>
        </label>
        <label className="font-mono text-xs text-(--color-text-dim)">
          Y:{" "}
          <select
            value={b}
            onChange={(e) => setB(e.target.value)}
            className="brand-select w-full text-xs"
          >
            {modelNames.map((m) => (
              <option key={m} value={m}>
                {modelLabel(m)}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="card mb-4">
        <ResponsiveContainer width="100%" height={340}>
          <ScatterChart margin={{ top: 20, right: 20, bottom: 20, left: 20 }}>
            <CartesianGrid stroke="rgba(255,255,255,0.04)" />
            <XAxis
              type="number"
              dataKey="x"
              name={a}
              domain={[0, 100]}
              tick={{
                fill: "var(--text-dim)",
                fontSize: 11,
                fontFamily: "var(--font-mono)",
              }}
              tickFormatter={(v: number) => `${v}%`}
              axisLine={false}
              tickLine={false}
              label={{
                value: `${a} similarity`,
                position: "bottom",
                fill: "var(--text-dim)",
                fontSize: 11,
                fontFamily: "var(--font-mono)",
              }}
            />
            <YAxis
              type="number"
              dataKey="y"
              name={b}
              domain={[0, 100]}
              tick={{
                fill: "var(--text-dim)",
                fontSize: 11,
                fontFamily: "var(--font-mono)",
              }}
              tickFormatter={(v: number) => `${v}%`}
              axisLine={false}
              tickLine={false}
              label={{
                value: `${b} similarity`,
                angle: -90,
                position: "left",
                fill: "var(--text-dim)",
                fontSize: 11,
                fontFamily: "var(--font-mono)",
              }}
            />
            <ZAxis range={[30, 30]} />
            <Tooltip
              content={({ active, payload, label }) => {
                if (!active || !payload || !payload.length) return null;
                const d = payload[0]?.payload;
                const aName = a || "";
                const bName = b || "";
                return (
                  <div
                    style={{
                      background: "var(--card)",
                      border: "1px solid var(--border)",
                      borderRadius: "8px",
                      padding: "8px 12px",
                      fontFamily: "var(--font-mono)",
                      fontSize: "0.72rem",
                      color: "var(--text)",
                    }}
                  >
                    <div style={{ marginBottom: 4, color: "var(--text-dim)" }}>
                      {d?.fixture || label}
                    </div>
                    <div>
                      {aName}: {d?.x}%
                    </div>
                    <div>
                      {bName}: {d?.y}%
                    </div>
                  </div>
                );
              }}
            />
            <Scatter
              data={scatterData}
              fill="#8884d8"
              shape={(props: any) => {
                const { cx, cy, payload } = props;
                return (
                  <a
                    href={`/fixtures/${encodeURIComponent(
                      payload.fixture.split("/")[0]
                    )}/${payload.fixture.split("/")[1]}`}
                  >
                    <circle
                      cx={cx}
                      cy={cy}
                      r={4}
                      fill={dotColor(payload.aPassed, payload.bPassed)}
                      opacity={0.7}
                      className="cursor-pointer"
                    />
                  </a>
                );
              }}
              isAnimationActive={false}
            />
          </ScatterChart>
        </ResponsiveContainer>
      </div>

      <div className="card mb-4">
        <div className="section-label">
          <span>Agreement Matrix</span>
        </div>
        <table className="data-table max-w-[400px]">
          <thead>
            <tr>
              <th></th>
              <th>{b} pass</th>
              <th>{b} fail</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td className="font-mono text-xs text-(--color-text-mid)">
                {a} pass
              </td>
              <td className="text-pass font-mono text-sm font-semibold">
                {bothPass}
              </td>
              <td className="text-(--color-warn) font-mono text-sm font-semibold">
                {aOnly}
              </td>
            </tr>
            <tr>
              <td className="font-mono text-xs text-(--color-text-mid)">
                {a} fail
              </td>
              <td className="text-(--color-warn) font-mono text-sm font-semibold">
                {bOnly}
              </td>
              <td className="text-fail font-mono text-sm font-semibold">
                {bothFail}
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      {scatterData.length > 0 && (
        <div className="card">
          <div className="section-label">
            <span>Per-Fixture Detail</span>
          </div>
          <table className="data-table">
            <thead>
              <tr>
                <th>Benchmark</th>
                <th>Fixture</th>
                <th>{a}</th>
                <th>{b}</th>
              </tr>
            </thead>
            <tbody>
              {scatterData.map((d) => {
                const [bench, fid] = d.fixture.split("/");
                return (
                  <tr key={d.fixture}>
                    <td className="font-mono text-xs text-(--color-text-mid)">
                      <a href={`/benchmarks/${bench}`} className="text-inherit">
                        {bench}
                      </a>
                    </td>
                    <td>
                      <a
                        href={`/fixtures/${encodeURIComponent(bench)}/${fid}`}
                        className="inline-flex items-center px-2 py-0.5 rounded font-mono text-xs bg-white/5 text-(--color-text-mid) border border-border no-underline"
                      >
                        {fid}
                      </a>
                    </td>
                    <td>
                      <Badge
                        variant="outline"
                        className={`font-mono text-[0.62rem] border-pass-border text-pass bg-pass-bg`}
                        style={{ opacity: d.aPassed ? 1 : 0.3 }}
                      >
                        {d.x}%
                      </Badge>
                    </td>
                    <td>
                      <Badge
                        variant="outline"
                        className={`font-mono text-[0.62rem] border-pass-border text-pass bg-pass-bg`}
                        style={{ opacity: d.bPassed ? 1 : 0.3 }}
                      >
                        {d.y}%
                      </Badge>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
