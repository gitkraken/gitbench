import { useState } from "react";
import {
  ChartScatter,
  CircleDollarSign,
  Clock3,
  Coins,
  type LucideIcon,
} from "lucide-react";
import CostValueChart from "@/components/charts/CostValueChart";
import QuadrantComparisonChart from "@/components/charts/QuadrantComparisonChart";
import RuntimeBarChart from "@/components/charts/RuntimeBarChart";
import TokenUsageChart from "@/components/charts/TokenUsageChart";

type FixtureMetricView = "quadrant" | "cost" | "runtime" | "tokens";

interface FixtureMetricSwitcherProps {
  benchmarkName: string;
  fixtureId: string;
}

interface FixtureMetricViewOption {
  id: FixtureMetricView;
  label: string;
  Icon: LucideIcon;
}

const VIEWS: FixtureMetricViewOption[] = [
  { id: "quadrant", label: "Quadrant", Icon: ChartScatter },
  { id: "cost", label: "Cost", Icon: CircleDollarSign },
  { id: "runtime", label: "API Time", Icon: Clock3 },
  { id: "tokens", label: "Tokens", Icon: Coins },
];

export default function FixtureMetricSwitcher({
  benchmarkName,
  fixtureId,
}: FixtureMetricSwitcherProps) {
  const [activeView, setActiveView] = useState<FixtureMetricView>("quadrant");

  return (
    <div>
      <div
        role="tablist"
        aria-label="Fixture metric view"
        className="mb-4 flex flex-wrap gap-2"
      >
        {VIEWS.map(({ id, label, Icon }) => {
          const active = id === activeView;
          return (
            <button
              key={id}
              type="button"
              role="tab"
              aria-selected={active}
              aria-controls={`fixture-metric-${id}`}
              title={label}
              className={`inline-flex h-9 items-center gap-2 rounded-md border px-3 font-mono text-[0.68rem] transition ${
                active
                  ? "border-(--accent) bg-(--accent)/10 text-(--accent)"
                  : "border-(--border) bg-white/3 text-(--text-dim) hover:border-white/20 hover:text-(--text)"
              }`}
              onClick={() => setActiveView(id)}
            >
              <Icon size={14} aria-hidden="true" />
              <span>{label}</span>
            </button>
          );
        })}
      </div>

      <div id={`fixture-metric-${activeView}`} role="tabpanel">
        {activeView === "quadrant" ? (
          <QuadrantComparisonChart
            benchmarkName={benchmarkName}
            fixtureId={fixtureId}
          />
        ) : null}
        {activeView === "cost" ? (
          <CostValueChart benchmarkName={benchmarkName} fixtureId={fixtureId} />
        ) : null}
        {activeView === "runtime" ? (
          <RuntimeBarChart benchmarkName={benchmarkName} fixtureId={fixtureId} />
        ) : null}
        {activeView === "tokens" ? (
          <TokenUsageChart
            benchmarkName={benchmarkName}
            fixtureId={fixtureId}
          />
        ) : null}
      </div>
    </div>
  );
}
