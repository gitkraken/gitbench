export function modelSlug(modelName: string): string {
  return encodeURIComponent(modelName).replace(/%/g, '~');
}

export function modelNameFromSlug(slug: string): string {
  return decodeURIComponent(slug.replace(/~/g, '%'));
}

export function modelPath(modelName: string): string {
  return `/models/${modelSlug(modelName)}`;
}
