export interface MultiSelectOptionLike {
  value: string;
  label: string;
  keywords?: string[];
}

export function filterMultiSelectOptions<T extends MultiSelectOptionLike>(
  options: T[],
  search: string,
): T[] {
  const normalizedSearch = search.trim().toLowerCase();
  if (!normalizedSearch) return options;
  return options.filter((option) =>
    [option.value, option.label, ...(option.keywords ?? [])]
      .join(" ")
      .toLowerCase()
      .includes(normalizedSearch),
  );
}

export function toggleMultiSelectValue(
  value: string[],
  toggled: string,
): string[] {
  return value.includes(toggled)
    ? value.filter((item) => item !== toggled)
    : [...value, toggled];
}

export function selectAllMultiSelectValues(
  options: MultiSelectOptionLike[],
): string[] {
  return options.map((option) => option.value);
}

export function clearMultiSelectValues(): string[] {
  return [];
}
