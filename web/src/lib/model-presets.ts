import type {
  BaseModelGroup,
  GitBenchData,
  ModelMetadata,
  ModelPreset,
} from "./types.ts";
import { loadModelMetadataCatalog } from "./model-catalog.ts";

const JSON_SCHEMA_SUFFIX = "__json_schema";

function canonicalGroupId(group: BaseModelGroup): string {
  return `${group.provider}/${group.baseModel}`;
}

function median(values: number[]): number {
  const sorted = [...values].sort((a, b) => a - b);
  const middle = Math.floor(sorted.length / 2);
  return sorted.length % 2
    ? sorted[middle]
    : (sorted[middle - 1] + sorted[middle]) / 2;
}

export function topPerformerGroupIds(
  summary: Pick<GitBenchData, "base_model_groups">,
  limit = 20,
): string[] {
  return summary.base_model_groups
    .map((group) => {
      const byMode = new Map<string, Set<number>>();
      for (const level of group.levels) {
        if (!Number.isFinite(level.pass_at_k)) continue;
        const mode = level.modelName.endsWith(JSON_SCHEMA_SUFFIX)
          ? "json_schema"
          : "text";
        const values = byMode.get(mode) ?? new Set<number>();
        values.add(level.pass_at_k);
        byMode.set(mode, values);
      }
      const modeMedians = [...byMode.values()]
        .filter((values) => values.size > 0)
        .map((values) => median([...values]));
      if (modeMedians.length === 0) return null;
      return {
        id: canonicalGroupId(group),
        score:
          modeMedians.reduce((total, value) => total + value, 0) /
          modeMedians.length,
      };
    })
    .filter((value): value is { id: string; score: number } => value !== null)
    .sort((a, b) => b.score - a.score || a.id.localeCompare(b.id))
    .slice(0, limit)
    .map(({ id }) => id);
}

function sortedMatchingIds(
  summary: Pick<GitBenchData, "base_model_groups">,
  metadata: Record<string, ModelMetadata>,
  include: (record: ModelMetadata, provider: string) => boolean,
): string[] {
  return summary.base_model_groups
    .map((group) => ({ id: canonicalGroupId(group), provider: group.provider }))
    .filter(({ id, provider }) => {
      const record = metadata[id];
      return record ? include(record, provider) : false;
    })
    .map(({ id }) => id)
    .sort((a, b) => a.localeCompare(b));
}

export function resolveModelPresets(
  summary: Pick<GitBenchData, "base_model_groups">,
  metadata: Record<string, ModelMetadata>,
): ModelPreset[] {
  const context = (
    include: (tokens: number) => boolean,
  ): string[] =>
    sortedMatchingIds(
      summary,
      metadata,
      (record) =>
        record.contextWindowTokens !== null &&
        include(record.contextWindowTokens),
    );

  return [
    {
      id: "top-performers",
      label: "Top Performers",
      description: "Top 20 base models by campaign-wide median overall pass rate.",
      modelGroupIds: topPerformerGroupIds(summary),
    },
    {
      id: "frontier-models",
      label: "Frontier Models",
      description: "Closed-weight models from OpenAI, Anthropic, and Google.",
      modelGroupIds: sortedMatchingIds(
        summary,
        metadata,
        (record, provider) =>
          record.weightAccess === "closed" &&
          (provider === "openai" ||
            provider === "anthropic" ||
            provider === "google"),
      ),
    },
    {
      id: "open-weights",
      label: "Open Weights",
      description: "Models with reviewed open-weight availability.",
      modelGroupIds: sortedMatchingIds(
        summary,
        metadata,
        (record) => record.weightAccess === "open",
      ),
    },
    {
      id: "context-up-to-200k",
      label: "Context: Up to 200K",
      description: "Known context windows up to and including 200K tokens.",
      modelGroupIds: context((tokens) => tokens <= 200_000),
    },
    {
      id: "context-200k-499k",
      label: "Context: 200K–499K",
      description: "Known context windows above 200K and below 500K tokens.",
      modelGroupIds: context(
        (tokens) => tokens > 200_000 && tokens < 500_000,
      ),
    },
    {
      id: "context-500k-999k",
      label: "Context: 500K–999K",
      description: "Known context windows from 500K up to one million tokens.",
      modelGroupIds: context(
        (tokens) => tokens >= 500_000 && tokens < 1_000_000,
      ),
    },
    {
      id: "context-1m-plus",
      label: "Context: 1M+",
      description: "Known context windows of at least one million tokens.",
      modelGroupIds: context((tokens) => tokens >= 1_000_000),
    },
  ];
}

export function attachModelPresets(
  summary: GitBenchData,
  metadataCatalog: Record<string, ModelMetadata> = loadModelMetadataCatalog().models,
): GitBenchData {
  const availableIds = new Set(summary.base_model_groups.map(canonicalGroupId));
  const modelMetadata = Object.fromEntries(
    Object.entries(metadataCatalog).filter(([id]) => availableIds.has(id)),
  );
  return {
    ...summary,
    model_metadata: modelMetadata,
    model_presets: resolveModelPresets(summary, modelMetadata),
  };
}
