import type {
  ModelMetadata,
  ModelMetadataCatalog,
} from "./types.ts";
import {
  validateModelMetadataCatalog,
  validateModelMetadataOverrides,
} from "./model-catalog.ts";

export interface OpenRouterModel {
  id: string;
  context_length?: number | null;
  hugging_face_id?: string | null;
}

export interface CatalogDiagnostics {
  unmatched: string[];
  unknownContext: string[];
  unknownWeightAccess: string[];
}

export interface GeneratedCatalog {
  catalog: ModelMetadataCatalog;
  diagnostics: CatalogDiagnostics;
}

function validUpstreamModels(input: unknown): OpenRouterModel[] {
  const records = Array.isArray(input)
    ? input
    : input && typeof input === "object" && Array.isArray((input as { data?: unknown }).data)
      ? (input as { data: unknown[] }).data
      : null;
  if (!records) throw new Error("OpenRouter response must contain a data array");

  return records.map((raw, index) => {
    if (!raw || typeof raw !== "object") {
      throw new Error(`OpenRouter model ${index} must be an object`);
    }
    const record = raw as Record<string, unknown>;
    if (typeof record.id !== "string" || !record.id.trim()) {
      throw new Error(`OpenRouter model ${index} has no valid id`);
    }
    const context = record.context_length;
    if (
      context !== undefined &&
      context !== null &&
      (!Number.isSafeInteger(context) || (context as number) < 0)
    ) {
      throw new Error(`OpenRouter model ${record.id} has invalid context_length`);
    }
    const huggingFace = record.hugging_face_id;
    if (
      huggingFace !== undefined &&
      huggingFace !== null &&
      typeof huggingFace !== "string"
    ) {
      throw new Error(`OpenRouter model ${record.id} has invalid hugging_face_id`);
    }
    return {
      id: record.id,
      context_length: context as number | null | undefined,
      hugging_face_id:
        typeof huggingFace === "string" && huggingFace.trim()
          ? huggingFace
          : null,
    };
  });
}

function uniqueCanonicalIds(ids: string[]): string[] {
  const unique = new Set(ids);
  if (unique.size !== ids.length) {
    throw new Error("current report model group IDs must be unique");
  }
  return [...unique].sort((a, b) => a.localeCompare(b));
}

export function generateModelCatalog(input: {
  currentModelGroupIds: string[];
  upstream: unknown;
  overrides: unknown;
  fetchedAt: string;
}): GeneratedCatalog {
  const canonicalIds = uniqueCanonicalIds(input.currentModelGroupIds);
  const overrides = validateModelMetadataOverrides(input.overrides);
  const upstream = validUpstreamModels(input.upstream);
  const upstreamById = new Map<string, OpenRouterModel>();
  for (const model of upstream) {
    if (upstreamById.has(model.id)) {
      throw new Error(`duplicate OpenRouter model ID: ${model.id}`);
    }
    upstreamById.set(model.id, model);
  }

  const models: Record<string, ModelMetadata> = {};
  const diagnostics: CatalogDiagnostics = {
    unmatched: [],
    unknownContext: [],
    unknownWeightAccess: [],
  };

  for (const canonicalId of canonicalIds) {
    const override = overrides.models[canonicalId];
    const upstreamId =
      override?.openRouterId ?? overrides.aliases[canonicalId] ?? canonicalId;
    const upstreamModel = upstreamById.get(upstreamId);
    if (!upstreamModel) diagnostics.unmatched.push(canonicalId);

    const hasContextOverride =
      override != null && "contextWindowTokens" in override;
    const contextWindowTokens = hasContextOverride
      ? (override.contextWindowTokens ?? null)
      : (upstreamModel?.context_length ?? null);
    const weightAccess = override?.weightAccess ?? "unknown";
    if (contextWindowTokens === null) diagnostics.unknownContext.push(canonicalId);
    if (weightAccess === "unknown") diagnostics.unknownWeightAccess.push(canonicalId);

    models[canonicalId] = {
      canonicalId,
      contextWindowTokens,
      weightAccess,
      openRouterId: upstreamModel?.id ?? null,
      huggingFaceId: upstreamModel?.hugging_face_id ?? null,
      provenance: {
        contextWindowTokens: hasContextOverride
          ? "override"
          : upstreamModel?.context_length != null
            ? "openrouter"
            : "unresolved",
        weightAccess: override?.weightAccess ? "override" : "unresolved",
      },
      fetchedAt: input.fetchedAt,
    };
  }

  const catalog = validateModelMetadataCatalog({
    schemaVersion: 1,
    fetchedAt: input.fetchedAt,
    models,
  });
  return { catalog, diagnostics };
}

export function serializeModelCatalog(catalog: ModelMetadataCatalog): string {
  validateModelMetadataCatalog(catalog);
  return `${JSON.stringify(catalog, null, 2)}\n`;
}
