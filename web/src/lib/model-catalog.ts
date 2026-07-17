import { readFileSync } from "node:fs";
import catalogSnapshot from "../../data/model-catalog.json" with { type: "json" };

import type {
  ModelMetadata,
  ModelMetadataCatalog,
  ModelMetadataOverride,
  ModelMetadataOverrides,
  ModelMetadataSource,
  ModelWeightAccess,
} from "./types.ts";

const WEIGHT_ACCESS = new Set<ModelWeightAccess>([
  "open",
  "closed",
  "unknown",
]);
const METADATA_SOURCES = new Set<ModelMetadataSource>([
  "openrouter",
  "override",
  "unresolved",
]);
const CANONICAL_ID = /^[^/\s]+\/[^/\s]+$/;

function object(value: unknown, label: string): Record<string, unknown> {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    throw new Error(`${label} must be an object`);
  }
  return value as Record<string, unknown>;
}

function isoTimestamp(value: unknown, label: string): string {
  if (
    typeof value !== "string" ||
    !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{3})?Z$/.test(value) ||
    Number.isNaN(Date.parse(value))
  ) {
    throw new Error(`${label} must be an ISO-8601 UTC timestamp`);
  }
  return value;
}

function nullableString(value: unknown, label: string): string | null {
  if (value === null) return null;
  if (typeof value !== "string" || !value.trim()) {
    throw new Error(`${label} must be a non-empty string or null`);
  }
  return value;
}

function contextWindow(value: unknown, label: string): number | null {
  if (value === null) return null;
  if (!Number.isSafeInteger(value) || (value as number) < 0) {
    throw new Error(`${label} must be a non-negative integer or null`);
  }
  return value as number;
}

function weightAccess(value: unknown, label: string): ModelWeightAccess {
  if (!WEIGHT_ACCESS.has(value as ModelWeightAccess)) {
    throw new Error(`${label} must be open, closed, or unknown`);
  }
  return value as ModelWeightAccess;
}

function source(value: unknown, label: string): ModelMetadataSource {
  if (!METADATA_SOURCES.has(value as ModelMetadataSource)) {
    throw new Error(`${label} must be openrouter, override, or unresolved`);
  }
  return value as ModelMetadataSource;
}

export function validateModelMetadataCatalog(
  input: unknown,
): ModelMetadataCatalog {
  const root = object(input, "catalog");
  if (root.schemaVersion !== 1) {
    throw new Error("catalog.schemaVersion must be 1");
  }
  const fetchedAt = isoTimestamp(root.fetchedAt, "catalog.fetchedAt");
  const records = object(root.models, "catalog.models");
  const ids = Object.keys(records);
  const sortedIds = [...ids].sort((a, b) => a.localeCompare(b));
  if (ids.some((id, index) => id !== sortedIds[index])) {
    throw new Error("catalog.models keys must use deterministic ascending order");
  }

  const models: Record<string, ModelMetadata> = {};
  for (const id of ids) {
    if (!CANONICAL_ID.test(id)) throw new Error(`invalid canonical model ID: ${id}`);
    const record = object(records[id], `catalog.models[${id}]`);
    if (record.canonicalId !== id) {
      throw new Error(`catalog record key/canonicalId mismatch for ${id}`);
    }
    const provenance = object(record.provenance, `${id}.provenance`);
    models[id] = {
      canonicalId: id,
      contextWindowTokens: contextWindow(
        record.contextWindowTokens,
        `${id}.contextWindowTokens`,
      ),
      weightAccess: weightAccess(record.weightAccess, `${id}.weightAccess`),
      openRouterId: nullableString(record.openRouterId, `${id}.openRouterId`),
      huggingFaceId: nullableString(record.huggingFaceId, `${id}.huggingFaceId`),
      provenance: {
        contextWindowTokens: source(
          provenance.contextWindowTokens,
          `${id}.provenance.contextWindowTokens`,
        ),
        weightAccess: source(
          provenance.weightAccess,
          `${id}.provenance.weightAccess`,
        ),
      },
      fetchedAt: isoTimestamp(record.fetchedAt, `${id}.fetchedAt`),
    };
  }
  return { schemaVersion: 1, fetchedAt, models };
}

export function validateModelMetadataOverrides(
  input: unknown,
): ModelMetadataOverrides {
  const root = object(input, "overrides");
  if (root.schemaVersion !== 1) {
    throw new Error("overrides.schemaVersion must be 1");
  }
  const aliasInput = object(root.aliases, "overrides.aliases");
  const modelInput = object(root.models, "overrides.models");
  const aliases: Record<string, string> = {};
  for (const [canonicalId, upstreamId] of Object.entries(aliasInput)) {
    if (!CANONICAL_ID.test(canonicalId)) {
      throw new Error(`invalid override alias canonical ID: ${canonicalId}`);
    }
    if (typeof upstreamId !== "string" || !upstreamId.trim()) {
      throw new Error(`override alias for ${canonicalId} must be a string`);
    }
    aliases[canonicalId] = upstreamId;
  }

  const models: Record<string, ModelMetadataOverride> = {};
  for (const [canonicalId, raw] of Object.entries(modelInput)) {
    if (!CANONICAL_ID.test(canonicalId)) {
      throw new Error(`invalid override canonical ID: ${canonicalId}`);
    }
    const value = object(raw, `overrides.models[${canonicalId}]`);
    const override: ModelMetadataOverride = {};
    if ("openRouterId" in value) {
      if (typeof value.openRouterId !== "string" || !value.openRouterId.trim()) {
        throw new Error(`${canonicalId}.openRouterId must be a non-empty string`);
      }
      override.openRouterId = value.openRouterId;
    }
    if ("contextWindowTokens" in value) {
      override.contextWindowTokens = contextWindow(
        value.contextWindowTokens,
        `${canonicalId}.contextWindowTokens`,
      );
    }
    if ("weightAccess" in value) {
      override.weightAccess = weightAccess(
        value.weightAccess,
        `${canonicalId}.weightAccess`,
      );
    }
    if ("note" in value) {
      if (typeof value.note !== "string" || !value.note.trim()) {
        throw new Error(`${canonicalId}.note must be a non-empty string`);
      }
      override.note = value.note;
    }
    models[canonicalId] = override;
  }
  return { schemaVersion: 1, aliases, models };
}

export function loadModelMetadataCatalog(
  path?: string | URL,
): ModelMetadataCatalog {
  return validateModelMetadataCatalog(
    path
      ? (JSON.parse(readFileSync(path, "utf8")) as unknown)
      : (catalogSnapshot as unknown),
  );
}
