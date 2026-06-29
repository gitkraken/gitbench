import { deflateSync, inflateSync } from "fflate";

export type ReportOutputMode = "text" | "json_schema" | "both";
export type ReportSelectionKind = "include" | "exclude" | "all";
export type ReportViewStateSource = "url" | "legacy" | "default";

export type ReportCodecErrorCode =
  | "unsupported-codec"
  | "invalid-base64"
  | "inflate-failed"
  | "invalid-json"
  | "invalid-payload"
  | "invalid-output-mode"
  | "unavailable-output-mode";

export interface ReportCodecError {
  code: ReportCodecErrorCode;
  message: string;
}

export interface ReportModelGroupLike {
  id: string;
  provider?: string;
  baseModel?: string;
  efforts?: Array<{
    modelName?: string;
  }>;
}

export interface DecodedReportViewState {
  selectionKind?: ReportSelectionKind;
  groupIds?: string[];
  outputMode?: ReportOutputMode;
  source: Exclude<ReportViewStateSource, "default">;
  errors: ReportCodecError[];
}

export interface ResolvedReportViewState {
  selectedGroups: string[];
  outputMode: ReportOutputMode;
  source: ReportViewStateSource;
  selectionKind: ReportSelectionKind;
  errors: ReportCodecError[];
}

export interface ReportViewStateInput {
  selectedGroups: string[];
  outputMode?: ReportOutputMode;
}

export interface ReportViewStateOptions {
  defaultSelectedGroups?: string[];
  defaultOutputMode?: ReportOutputMode;
  availableOutputModes?: Iterable<string>;
  maxReadableLength?: number;
  pathname?: string;
}

interface CompactReportViewState {
  v: 1;
  k: "i" | "x" | "a";
  g?: string[];
  o?: "t" | "j" | "b";
}

interface EncodedSelection {
  kind: ReportSelectionKind;
  groupIds: string[];
}

type BufferLike = Uint8Array & { toString(encoding: string): string };
type BufferConstructorLike = {
  from(input: Uint8Array): BufferLike;
  from(input: string, encoding: string): BufferLike;
};

const COMPRESSED_PARAM = "s";
const CODEC_PREFIX = "gb1.";
const DEFAULT_MAX_READABLE_LENGTH = 1800;
const TEXT_ENCODER = new TextEncoder();
const TEXT_DECODER = new TextDecoder();
const REPORT_QUERY_KEYS = [
  COMPRESSED_PARAM,
  "m",
  "model",
  "x",
  "exclude",
  "models",
  "mode",
  "with",
];

function codecError(
  code: ReportCodecErrorCode,
  message: string
): ReportCodecError {
  return { code, message };
}

function bufferConstructor(): BufferConstructorLike | undefined {
  return (globalThis as unknown as { Buffer?: BufferConstructorLike }).Buffer;
}

function bytesToBinary(bytes: Uint8Array): string {
  const chunkSize = 0x8000;
  let binary = "";
  for (let index = 0; index < bytes.length; index += chunkSize) {
    binary += String.fromCharCode(
      ...bytes.subarray(index, index + chunkSize)
    );
  }
  return binary;
}

function binaryToBytes(binary: string): Uint8Array {
  const bytes = new Uint8Array(binary.length);
  for (let index = 0; index < binary.length; index += 1) {
    bytes[index] = binary.charCodeAt(index);
  }
  return bytes;
}

export function base64UrlEncodeBytes(bytes: Uint8Array): string {
  const buffer = bufferConstructor();
  const base64 =
    typeof btoa === "function"
      ? btoa(bytesToBinary(bytes))
      : buffer?.from(bytes).toString("base64");
  if (!base64) {
    throw new Error("No base64 encoder is available in this environment.");
  }
  return base64.replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/g, "");
}

export function base64UrlDecodeBytes(payload: string): Uint8Array {
  if (!/^[A-Za-z0-9_-]*$/.test(payload) || payload.length % 4 === 1) {
    throw new Error("Invalid base64url payload.");
  }

  const padded = payload
    .replace(/-/g, "+")
    .replace(/_/g, "/")
    .padEnd(Math.ceil(payload.length / 4) * 4, "=");
  const buffer = bufferConstructor();
  if (typeof atob === "function") {
    return binaryToBytes(atob(padded));
  }
  if (buffer) {
    return new Uint8Array(buffer.from(padded, "base64"));
  }
  throw new Error("No base64 decoder is available in this environment.");
}

function compactKind(kind: ReportSelectionKind): CompactReportViewState["k"] {
  if (kind === "include") return "i";
  if (kind === "exclude") return "x";
  return "a";
}

function expandCompactKind(kind: unknown): ReportSelectionKind | null {
  if (kind === "i") return "include";
  if (kind === "x") return "exclude";
  if (kind === "a") return "all";
  return null;
}

function compactOutputMode(mode?: ReportOutputMode): CompactReportViewState["o"] {
  if (mode === "text") return "t";
  if (mode === "json_schema") return "j";
  if (mode === "both") return "b";
  return undefined;
}

function expandCompactOutputMode(mode: unknown): ReportOutputMode | null | undefined {
  if (mode === undefined) return undefined;
  if (mode === "t") return "text";
  if (mode === "j") return "json_schema";
  if (mode === "b") return "both";
  return null;
}

function isReportOutputMode(value: unknown): value is ReportOutputMode {
  return value === "text" || value === "json_schema" || value === "both";
}

function asSearchParams(searchParams: URLSearchParams | string): URLSearchParams {
  return searchParams instanceof URLSearchParams
    ? new URLSearchParams(searchParams)
    : new URLSearchParams(searchParams.startsWith("?") ? searchParams.slice(1) : searchParams);
}

function csvValues(values: string[]): string[] {
  return values
    .flatMap((value) => value.split(","))
    .map((value) => value.trim())
    .filter(Boolean);
}

function unique(values: string[]): string[] {
  const seen = new Set<string>();
  const result: string[] = [];
  for (const value of values) {
    if (seen.has(value)) continue;
    seen.add(value);
    result.push(value);
  }
  return result;
}

function stripJsonSchemaSuffix(value: string): string {
  return value.endsWith("__json_schema")
    ? value.slice(0, -"__json_schema".length)
    : value;
}

function aliasesForEffort(modelName: string): string[] {
  const clean = stripJsonSchemaSuffix(modelName);
  const aliases = new Set<string>([modelName, clean]);
  aliases.add(clean.replace(/:([^:]*)$/, "#$1"));

  if (clean.includes("/")) {
    const shortName = clean.slice(clean.indexOf("/") + 1);
    aliases.add(shortName);
    aliases.add(shortName.replace(/:([^:]*)$/, "#$1"));
  }

  return Array.from(aliases).filter(Boolean);
}

function addAlias(
  aliases: Map<string, string>,
  conflicts: Set<string>,
  alias: string | undefined,
  groupId: string
): void {
  if (!alias) return;
  const existing = aliases.get(alias);
  if (existing && existing !== groupId) {
    conflicts.add(alias);
    return;
  }
  if (!conflicts.has(alias)) aliases.set(alias, groupId);
}

function groupAliasMap(groups: ReportModelGroupLike[]): Map<string, string> {
  const aliases = new Map<string, string>();
  const conflicts = new Set<string>();

  for (const group of groups) {
    addAlias(aliases, conflicts, group.id, group.id);
    addAlias(aliases, conflicts, group.baseModel, group.id);
    if (group.provider && group.baseModel) {
      addAlias(aliases, conflicts, `${group.provider}/${group.baseModel}`, group.id);
    }
    for (const effort of group.efforts ?? []) {
      for (const alias of aliasesForEffort(effort.modelName ?? "")) {
        addAlias(aliases, conflicts, alias, group.id);
      }
    }
  }

  for (const alias of conflicts) aliases.delete(alias);
  return aliases;
}

export function sanitizeReportGroupIds(
  values: string[],
  groups: ReportModelGroupLike[]
): string[] {
  const aliases = groupAliasMap(groups);
  const result: string[] = [];
  const seen = new Set<string>();

  for (const value of values) {
    const groupId = aliases.get(stripJsonSchemaSuffix(value)) ?? aliases.get(value);
    if (!groupId || seen.has(groupId)) continue;
    seen.add(groupId);
    result.push(groupId);
  }

  return result;
}

function availableModes(options: ReportViewStateOptions): Set<string> | null {
  if (!options.availableOutputModes) return null;
  return new Set(options.availableOutputModes);
}

function modeIsAvailable(
  mode: ReportOutputMode,
  modes: Set<string> | null
): boolean {
  if (!modes || modes.size === 0) return true;
  if (mode === "both") {
    return modes.has("text") && modes.has("json_schema");
  }
  return modes.has(mode);
}

function defaultOutputMode(options: ReportViewStateOptions): ReportOutputMode {
  const modes = availableModes(options);
  const configured = options.defaultOutputMode;
  if (configured && modeIsAvailable(configured, modes)) return configured;
  if (modeIsAvailable("both", modes)) return "both";
  if (modeIsAvailable("text", modes)) return "text";
  if (modeIsAvailable("json_schema", modes)) return "json_schema";
  return "text";
}

function resolveOutputMode(
  decodedMode: ReportOutputMode | undefined,
  options: ReportViewStateOptions,
  errors: ReportCodecError[]
): ReportOutputMode {
  const fallback = defaultOutputMode(options);
  if (!decodedMode) return fallback;
  if (modeIsAvailable(decodedMode, availableModes(options))) return decodedMode;
  errors.push(
    codecError(
      "unavailable-output-mode",
      `Output mode "${decodedMode}" is not available for the current report.`
    )
  );
  return fallback;
}

function defaultSelection(
  groups: ReportModelGroupLike[],
  options: ReportViewStateOptions
): string[] {
  const explicitDefault = options.defaultSelectedGroups
    ? sanitizeReportGroupIds(options.defaultSelectedGroups, groups)
    : [];
  return explicitDefault.length > 0
    ? explicitDefault
    : groups.map((group) => group.id);
}

function resolveSelection(
  decoded: DecodedReportViewState | null,
  groups: ReportModelGroupLike[],
  options: ReportViewStateOptions
): { selectedGroups: string[]; selectionKind: ReportSelectionKind; source: ReportViewStateSource } {
  const allGroupIds = groups.map((group) => group.id);
  const fallback = defaultSelection(groups, options);
  if (!decoded?.selectionKind) {
    const source =
      decoded && (decoded.outputMode || decoded.errors.length === 0)
        ? decoded.source
        : "default";
    return {
      selectedGroups: fallback,
      selectionKind: fallback.length === allGroupIds.length ? "all" : "include",
      source,
    };
  }

  if (decoded.selectionKind === "all") {
    return { selectedGroups: allGroupIds, selectionKind: "all", source: decoded.source };
  }

  const decodedIds = sanitizeReportGroupIds(decoded.groupIds ?? [], groups);
  if (decoded.selectionKind === "exclude") {
    const excluded = new Set(decodedIds);
    return {
      selectedGroups: allGroupIds.filter((groupId) => !excluded.has(groupId)),
      selectionKind: "exclude",
      source: decoded.source,
    };
  }

  if ((decoded.groupIds ?? []).length === 0) {
    return {
      selectedGroups: [],
      selectionKind: "include",
      source: decoded.source,
    };
  }

  if (decodedIds.length > 0) {
    return {
      selectedGroups: decodedIds,
      selectionKind: "include",
      source: decoded.source,
    };
  }

  return {
    selectedGroups: fallback,
    selectionKind: fallback.length === allGroupIds.length ? "all" : "include",
    source: "default",
  };
}

function decodeCompactPayload(
  payload: unknown
): Omit<DecodedReportViewState, "source"> {
  const errors: ReportCodecError[] = [];
  if (!payload || typeof payload !== "object") {
    return {
      errors: [
        codecError("invalid-payload", "Compressed report state is not an object."),
      ],
    };
  }

  const value = payload as Partial<CompactReportViewState>;
  const kind = expandCompactKind(value.k);
  if (value.v !== 1 || !kind) {
    return {
      errors: [
        codecError("invalid-payload", "Compressed report state payload is invalid."),
      ],
    };
  }

  const outputMode = expandCompactOutputMode(value.o);
  if (outputMode === null) {
    errors.push(
      codecError(
        "invalid-output-mode",
        "Compressed report state contains an invalid output mode."
      )
    );
  }

  return {
    selectionKind: kind,
    groupIds:
      kind === "all"
        ? []
        : Array.isArray(value.g)
        ? value.g.filter((item): item is string => typeof item === "string")
        : [],
    outputMode: outputMode ?? undefined,
    errors,
  };
}

function decodeCompressedReportViewState(
  value: string
): DecodedReportViewState {
  if (!value.startsWith(CODEC_PREFIX)) {
    return {
      source: "url",
      errors: [
        codecError(
          "unsupported-codec",
          "Compressed report state uses an unsupported codec prefix."
        ),
      ],
    };
  }

  try {
    const compressed = base64UrlDecodeBytes(value.slice(CODEC_PREFIX.length));
    const json = TEXT_DECODER.decode(inflateSync(compressed));
    const decoded = decodeCompactPayload(JSON.parse(json));
    return { ...decoded, source: "url" };
  } catch (error) {
    if (error instanceof SyntaxError) {
      return {
        source: "url",
        errors: [
          codecError("invalid-json", "Compressed report state is not valid JSON."),
        ],
      };
    }
    const message = error instanceof Error ? error.message : String(error);
    const code = message.includes("base64")
      ? "invalid-base64"
      : "inflate-failed";
    return {
      source: "url",
      errors: [
        codecError(code, "Compressed report state could not be decoded."),
      ],
    };
  }
}

function parseReadableOutputMode(params: URLSearchParams): {
  outputMode?: ReportOutputMode;
  errors: ReportCodecError[];
} {
  const mode = params.get("mode");
  if (!mode) return { errors: [] };
  if (isReportOutputMode(mode)) return { outputMode: mode, errors: [] };
  return {
    errors: [
      codecError("invalid-output-mode", `Invalid output mode "${mode}".`),
    ],
  };
}

function decodeReadableReportViewState(
  params: URLSearchParams
): DecodedReportViewState | null {
  const errors = parseReadableOutputMode(params).errors;
  const outputMode = parseReadableOutputMode(params).outputMode;
  const models = params.get("models");
  const all = models === "all";
  const none = models === "none";
  const include = unique([
    ...csvValues(params.getAll("m")),
    ...csvValues(params.getAll("model")),
  ]);
  const exclude = unique([
    ...csvValues(params.getAll("x")),
    ...csvValues(params.getAll("exclude")),
  ]);

  if (all) {
    return {
      selectionKind: "all",
      groupIds: [],
      outputMode,
      source: "url",
      errors,
    };
  }
  if (none) {
    return {
      selectionKind: "include",
      groupIds: [],
      outputMode,
      source: "url",
      errors,
    };
  }
  if (include.length > 0) {
    return {
      selectionKind: "include",
      groupIds: include,
      outputMode,
      source: "url",
      errors,
    };
  }
  if (exclude.length > 0) {
    return {
      selectionKind: "exclude",
      groupIds: exclude,
      outputMode,
      source: "url",
      errors,
    };
  }
  if (outputMode || errors.length > 0) {
    return { outputMode, source: "url", errors };
  }
  return null;
}

function decodeLegacyWithState(
  params: URLSearchParams
): DecodedReportViewState | null {
  const withValues = unique(csvValues(params.getAll("with")));
  if (withValues.length === 0) return null;
  const mode = parseReadableOutputMode(params);
  return {
    selectionKind: "include",
    groupIds: withValues,
    outputMode: mode.outputMode,
    source: "legacy",
    errors: mode.errors,
  };
}

export function decodeReportViewState(
  searchParams: URLSearchParams | string
): DecodedReportViewState | null {
  const params = asSearchParams(searchParams);
  const compressed = params.get(COMPRESSED_PARAM);
  if (compressed) return decodeCompressedReportViewState(compressed);
  return decodeReadableReportViewState(params) ?? decodeLegacyWithState(params);
}

export function resolveReportViewState(
  searchParams: URLSearchParams | string,
  groups: ReportModelGroupLike[],
  options: ReportViewStateOptions = {}
): ResolvedReportViewState {
  const decoded = decodeReportViewState(searchParams);
  const errors = [...(decoded?.errors ?? [])];
  const selection = resolveSelection(decoded, groups, options);
  return {
    selectedGroups: selection.selectedGroups,
    outputMode: resolveOutputMode(decoded?.outputMode, options, errors),
    source: selection.source,
    selectionKind: selection.selectionKind,
    errors,
  };
}

function selectionForEncoding(
  state: ReportViewStateInput,
  groups: ReportModelGroupLike[]
): EncodedSelection {
  const allGroupIds = groups.map((group) => group.id);
  const selectedGroups = sanitizeReportGroupIds(state.selectedGroups, groups);
  if (selectedGroups.length === allGroupIds.length) {
    return { kind: "all", groupIds: [] };
  }

  const selected = new Set(selectedGroups);
  const excluded = allGroupIds.filter((groupId) => !selected.has(groupId));
  return selectedGroups.length <= excluded.length
    ? { kind: "include", groupIds: selectedGroups }
    : { kind: "exclude", groupIds: excluded };
}

function encodePathComponent(value: string): string {
  return encodeURIComponent(value);
}

function encodeReadableReportViewState(
  selection: EncodedSelection,
  outputMode: ReportOutputMode
): string {
  const parts: string[] = [];
  if (selection.kind === "all") {
    parts.push("models=all");
  } else if (selection.kind === "include") {
    if (selection.groupIds.length === 0) {
      parts.push("models=none");
    } else {
      parts.push(`m=${selection.groupIds.map(encodePathComponent).join(",")}`);
    }
  } else {
    parts.push(`x=${selection.groupIds.map(encodePathComponent).join(",")}`);
  }

  if (outputMode !== "both") {
    parts.push(`mode=${outputMode}`);
  }
  return parts.join("&");
}

function encodeCompressedReportViewState(
  selection: EncodedSelection,
  outputMode: ReportOutputMode
): string {
  const payload: CompactReportViewState = {
    v: 1,
    k: compactKind(selection.kind),
  };
  if (selection.kind !== "all") payload.g = selection.groupIds;
  const compactMode = compactOutputMode(outputMode);
  if (compactMode && compactMode !== "b") payload.o = compactMode;

  const compressed = deflateSync(TEXT_ENCODER.encode(JSON.stringify(payload)));
  return `${COMPRESSED_PARAM}=${CODEC_PREFIX}${base64UrlEncodeBytes(compressed)}`;
}

export function encodeReportViewState(
  state: ReportViewStateInput,
  groups: ReportModelGroupLike[],
  options: ReportViewStateOptions = {}
): string {
  const selection = selectionForEncoding(state, groups);
  const outputMode = resolveOutputMode(state.outputMode, options, []);
  const readable = encodeReadableReportViewState(selection, outputMode);
  const compressed = encodeCompressedReportViewState(selection, outputMode);
  const pathname = options.pathname ?? "";
  const maxReadableLength =
    options.maxReadableLength ?? DEFAULT_MAX_READABLE_LENGTH;
  const readableLength = pathname.length + (readable ? readable.length + 1 : 0);

  if (readableLength > maxReadableLength || compressed.length < readable.length) {
    return compressed;
  }
  return readable;
}

export function stripReportViewStateParams(
  searchParams: URLSearchParams | string
): URLSearchParams {
  const params = asSearchParams(searchParams);
  for (const key of REPORT_QUERY_KEYS) params.delete(key);
  return params;
}

export function applyReportViewStateToSearchParams(
  searchParams: URLSearchParams | string,
  state: ReportViewStateInput,
  groups: ReportModelGroupLike[],
  options: ReportViewStateOptions = {}
): URLSearchParams {
  const params = stripReportViewStateParams(searchParams);
  const encoded = new URLSearchParams(
    encodeReportViewState(state, groups, options)
  );
  for (const [key, value] of encoded.entries()) {
    params.append(key, value);
  }
  return params;
}

export function writeReportViewStateToHistory(
  state: ReportViewStateInput,
  groups: ReportModelGroupLike[],
  options: ReportViewStateOptions = {}
): boolean {
  if (typeof window === "undefined") return false;

  const url = new URL(window.location.href);
  const nextParams = applyReportViewStateToSearchParams(
    url.searchParams,
    state,
    groups,
    { ...options, pathname: url.pathname }
  );
  const nextSearch = nextParams.toString();
  const nextUrl = `${url.pathname}${nextSearch ? `?${nextSearch}` : ""}${
    url.hash
  }`;
  const currentUrl = `${url.pathname}${url.search}${url.hash}`;
  if (nextUrl === currentUrl) return false;

  window.history.replaceState(window.history.state, "", nextUrl);
  return true;
}
