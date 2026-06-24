import { useEffect, useState } from "react";
import { loadFixtureAttempts } from "@/lib/report-client";
import type {
  FixtureAttempts,
  FixtureAttemptGroup,
  RawAttempt,
} from "@/lib/report-store";
import { useCampaignId } from "@/lib/use-campaign";
import { Badge } from "@/components/ui/badge";

function classificationLabel(classification: string): string {
  switch (classification) {
    case "stable_pass":
      return "stable pass";
    case "stable_fail":
      return "stable fail";
    case "flaky":
      return "flaky";
    default:
      return "unknown";
  }
}

function classificationColor(classification: string): string {
  switch (classification) {
    case "stable_pass":
      return "text-pass bg-pass-bg border-pass-border";
    case "stable_fail":
      return "text-fail bg-fail-bg border-(--color-fail-border)";
    case "flaky":
      return "text-(--color-warn) bg-warn-bg border-(--color-warn-border)";
    default:
      return "text-(--color-text-mid) bg-(--color-card) border-border";
  }
}

function AttemptRow({ attempt }: { attempt: RawAttempt }) {
  return (
    <tr className="border-b border-(--color-border-dim)">
      <td className="py-1.5 pr-3 font-mono text-[0.65rem] text-(--color-text-dim)">
        Trial {attempt.trial_index}
      </td>
      <td className="py-1.5 pr-3 font-mono text-[0.65rem] text-(--color-text-dim)">
        {attempt.reasoning_level ?? "default"}
      </td>
      <td className="py-1.5 pr-3">
        <Badge
          variant="outline"
          className={`font-mono text-[0.6rem] ${
            attempt.passed
              ? "text-pass bg-pass-bg border-pass-border"
              : attempt.status === "valid_fail"
              ? "text-fail bg-fail-bg border-(--color-fail-border)"
              : "text-(--color-warn) bg-warn-bg border-(--color-warn-border)"
          }`}
        >
          {attempt.status}
        </Badge>
      </td>
      <td className="py-1.5 pr-3 text-right font-mono text-[0.65rem] text-(--color-text-dim)">
        {attempt.similarity != null
          ? `${(attempt.similarity * 100).toFixed(1)}%`
          : "—"}
      </td>
      <td className="py-1.5 pr-3 text-right font-mono text-[0.65rem] text-(--color-text-dim)">
        {attempt.input_tokens ?? "—"}
      </td>
      <td className="py-1.5 pr-3 text-right font-mono text-[0.65rem] text-(--color-text-dim)">
        {attempt.output_tokens ?? "—"}
      </td>
      <td className="py-1.5 pr-3 text-right font-mono text-[0.65rem] text-(--color-text-dim)">
        {attempt.cost_usd != null ? `$${attempt.cost_usd.toFixed(6)}` : "—"}
      </td>
      <td className="py-1.5 text-right font-mono text-[0.65rem] text-(--color-text-dim)">
        {attempt.api_duration_ms != null
          ? `${attempt.api_duration_ms.toFixed(0)}ms`
          : "—"}
      </td>
    </tr>
  );
}

function ModelModeGroup({
  group,
  attempts,
}: {
  group: FixtureAttemptGroup;
  attempts: RawAttempt[];
}) {
  const rate =
    group.mean_success_rate != null
      ? `${(group.mean_success_rate * 100).toFixed(1)}%`
      : "—";

  return (
    <details className="group border border-(--color-border) rounded-md overflow-hidden mb-3">
      <summary className="flex items-center gap-3 p-3 cursor-pointer bg-(--color-card) hover:bg-(--color-surface) list-none select-none">
        <span className="font-mono text-xs text-(--color-text)">
          {group.model_name}
        </span>
        <Badge variant="outline" className="font-mono text-[0.6rem]">
          {group.output_mode}
        </Badge>
        <Badge
          variant="outline"
          className={`font-mono text-[0.6rem] ${classificationColor(
            group.classification
          )}`}
        >
          {classificationLabel(group.classification)}
        </Badge>
        <span className="ml-auto font-mono text-[0.65rem] text-(--color-text-mid)">
          {rate} · {group.passing_attempts}/{group.valid_attempts} valid ·{" "}
          {group.completed_trials}/{group.planned_trials} trials
        </span>
      </summary>
      <div className="p-3 border-t border-(--color-border)">
        <table className="w-full text-left">
          <thead>
            <tr className="text-(--color-text-dim) border-b border-border font-mono text-[0.65rem]">
              <th className="pb-1.5 pr-3 font-normal">Trial</th>
              <th className="pb-1.5 pr-3 font-normal">Effort</th>
              <th className="pb-1.5 pr-3 font-normal">Status</th>
              <th className="pb-1.5 pr-3 font-normal text-right">Similarity</th>
              <th className="pb-1.5 pr-3 font-normal text-right">Input</th>
              <th className="pb-1.5 pr-3 font-normal text-right">Output</th>
              <th className="pb-1.5 pr-3 font-normal text-right">Cost</th>
              <th className="pb-1.5 font-normal text-right">API time</th>
            </tr>
          </thead>
          <tbody>
            {attempts
              .filter(
                (a) =>
                  a.model_name === group.model_name &&
                  a.output_mode === group.output_mode
              )
              .map((attempt) => (
                <AttemptRow
                  key={`${attempt.trial_index}-${attempt.model_name}`}
                  attempt={attempt}
                />
              ))}
          </tbody>
        </table>
      </div>
    </details>
  );
}

export interface FixtureCampaignDetailProps {
  benchmark: string;
  fixture: string;
}

export function FixtureCampaignDetail({
  benchmark,
  fixture,
}: FixtureCampaignDetailProps) {
  const [data, setData] = useState<FixtureAttempts | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const campaignId = useCampaignId();

  useEffect(() => {
    setLoading(true);
    setError(null);
    loadFixtureAttempts(benchmark, fixture)
      .then(setData)
      .catch((err) => {
        setError(err instanceof Error ? err.message : String(err));
      })
      .finally(() => setLoading(false));
  }, [benchmark, fixture, campaignId]);

  if (loading) {
    return (
      <div className="text-sm text-(--color-text-mid)">
        Loading raw attempt evidence…
      </div>
    );
  }
  if (error) {
    return (
      <div className="text-sm text-red-500">
        Raw attempt evidence unavailable
      </div>
    );
  }
  if (!data || data.groups.length === 0) {
    return (
      <div className="text-sm text-(--color-text-mid)">
        No repeated-trial attempts recorded for this fixture.
      </div>
    );
  }

  return (
    <div>
      {data.groups.map((group) => (
        <ModelModeGroup
          key={`${group.model_name}-${group.output_mode}`}
          group={group}
          attempts={data.attempts}
        />
      ))}
    </div>
  );
}
