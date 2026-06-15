export function modelSlug(modelName: string): string {
  return encodeURIComponent(modelName).replace(/%/g, "~");
}

export function modelNameFromSlug(slug: string): string {
  return decodeURIComponent(slug.replace(/~/g, "%"));
}

function encodeRouteSegment(value: string): string {
  return encodeURIComponent(value);
}

function stripOutputModeSuffix(modelName: string): string {
  return modelName.endsWith("__json_schema")
    ? modelName.slice(0, -"__json_schema".length)
    : modelName;
}

export function modelPath(modelName: string): string {
  const cleanName = stripOutputModeSuffix(modelName);
  let provider = cleanName;
  let baseModel = cleanName;
  let level = "default";

  if (cleanName.includes("/")) {
    const slashIndex = cleanName.indexOf("/");
    const rest = cleanName.slice(slashIndex + 1);
    provider = cleanName.slice(0, slashIndex);
    baseModel = rest;
    if (rest.includes(":")) {
      const parts = rest.split(":");
      level = parts.pop() || "default";
      baseModel = parts.join(":");
    } else if (rest.includes("#")) {
      const parts = rest.split("#");
      level = parts.pop() || "default";
      baseModel = parts.join("#");
    }
  }

  return modelLevelPath(provider, baseModel, level);
}

export function modelGroupPath(provider: string, baseModel: string): string {
  return `/models/${encodeRouteSegment(provider)}/${encodeRouteSegment(
    baseModel
  )}/`;
}

export function modelLevelPath(
  provider: string,
  baseModel: string,
  level: string
): string {
  return `/models/${encodeRouteSegment(provider)}/${encodeRouteSegment(
    baseModel
  )}/${encodeRouteSegment(level)}/`;
}
