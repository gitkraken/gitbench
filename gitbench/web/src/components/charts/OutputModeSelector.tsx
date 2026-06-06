import type { OutputMode } from "@/components/charts/model-groups";

interface OutputModeSelectorProps {
  value: OutputMode;
  onChange: (mode: OutputMode) => void;
  availableModes: Set<string>;
}

const MODE_LABELS: Record<string, string> = {
  text: "Text",
  json_schema: "JSON",
};

export default function OutputModeSelector({
  value,
  onChange,
  availableModes,
}: OutputModeSelectorProps) {
  const hasText = availableModes.has("text");
  const hasJson = availableModes.has("json_schema");

  // If only one mode is available, don't show the selector
  if (!hasText || !hasJson) return null;

  return (
    <div className="flex items-center gap-1 rounded-lg border border-border bg-(--color-surface) p-0.5">
      <button
        type="button"
        className={`rounded-md px-3 py-1.5 text-xs font-mono font-medium transition-colors ${
          value === "text"
            ? "bg-(--color-accent) text-(--color-accent-fg)"
            : "text-(--color-text-dim) hover:text-(--color-text)"
        }`}
        onClick={() => onChange("text")}
      >
        Text
      </button>
      <button
        type="button"
        className={`rounded-md px-3 py-1.5 text-xs font-mono font-medium transition-colors ${
          value === "json_schema"
            ? "bg-(--color-accent) text-(--color-accent-fg)"
            : "text-(--color-text-dim) hover:text-(--color-text)"
        }`}
        onClick={() => onChange("json_schema")}
      >
        JSON
      </button>
      <button
        type="button"
        className={`rounded-md px-3 py-1.5 text-xs font-mono font-medium transition-colors ${
          value === "both"
            ? "bg-(--color-accent) text-(--color-accent-fg)"
            : "text-(--color-text-dim) hover:text-(--color-text)"
        }`}
        onClick={() => onChange("both")}
      >
        Both
      </button>
    </div>
  );
}
