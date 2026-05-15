export function modelSlug(modelName: string): string {
  return encodeURIComponent(modelName).replace(/%/g, '~');
}

export function modelNameFromSlug(slug: string): string {
  return decodeURIComponent(slug.replace(/~/g, '%'));
}

// Legacy/comparison URL helper — use modelLevelPath() for new nested routes
export function modelPath(modelName: string): string {
  return `/models/${modelSlug(modelName)}`;
}

export function modelGroupPath(provider: string, baseModel: string): string {
  return `/models/${provider}/${baseModel}/`;
}

export function modelLevelPath(provider: string, baseModel: string, level: string): string {
  return `/models/${provider}/${baseModel}/${level}/`;
}
