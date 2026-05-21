import ProviderIcon from "@/components/ProviderIcon";
import { getProviderColor } from "@/lib/provider-colors";
import type { GroupedMetricRow } from "./model-groups";

export function truncateName(name: string, maxLen = 16): string {
  if (!name || name.length <= maxLen) return name || "";
  return `${name.slice(0, maxLen - 1)}…`;
}

export function providerLegend(rows: GroupedMetricRow[]) {
  const seen = new Set<string>();
  const providers: { slug: string; color: string }[] = [];
  for (const row of rows) {
    const key = row.provider.toLowerCase();
    if (seen.has(key)) continue;
    seen.add(key);
    providers.push({ slug: row.provider, color: getProviderColor(row.provider) });
  }
  return providers;
}

export function ProviderLegend({ rows }: { rows: GroupedMetricRow[] }) {
  const providers = providerLegend(rows);
  if (providers.length === 0) return null;
  return (
    <div
      style={{
        display: "flex",
        flexWrap: "wrap",
        gap: 14,
        justifyContent: "center",
        marginTop: 10,
        fontSize: 10,
        fontFamily: "var(--font-mono)",
        color: "var(--text-dim)",
      }}
    >
      {providers.map((provider) => (
        <span
          key={provider.slug}
          style={{ display: "inline-flex", alignItems: "center", gap: 5 }}
        >
          <span
            style={{
              width: 8,
              height: 8,
              borderRadius: "50%",
              backgroundColor: provider.color,
              flexShrink: 0,
            }}
          />
          {provider.slug}
        </span>
      ))}
    </div>
  );
}

interface TickProps {
  x: number;
  y: number;
  payload: { value: string };
  rowMap?: Record<string, GroupedMetricRow>;
}

export function VerticalGroupTick({ x, y, payload, rowMap }: TickProps) {
  const row = rowMap?.[payload.value];
  return (
    <g transform={`translate(${x},${y})`}>
      <g transform="rotate(-40)">
        <foreignObject x={-138} y={-6} width={138} height={32} style={{ overflow: "visible" }}>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 3,
              fontSize: 9,
              fontFamily: "var(--font-mono)",
              color: "var(--text-mid)",
              justifyContent: "flex-end",
              width: 138,
            }}
          >
            <ProviderIcon provider={row?.provider ?? ""} size={12} />
            <span
              style={{
                overflow: "hidden",
                textOverflow: "ellipsis",
                whiteSpace: "nowrap",
                maxWidth: 118,
              }}
            >
              {row?.baseModel ?? payload.value}
            </span>
          </div>
        </foreignObject>
      </g>
    </g>
  );
}

export function HorizontalGroupTick({ x, y, payload, rowMap }: TickProps) {
  const row = rowMap?.[payload.value];
  return (
    <g transform={`translate(${x},${y})`}>
      <foreignObject x={-112} y={-10} width={106} height={22} style={{ overflow: "visible" }}>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "flex-end",
            gap: 4,
            fontSize: 10,
            fontFamily: "var(--font-mono)",
            color: "var(--text-mid)",
            whiteSpace: "nowrap",
          }}
        >
          <ProviderIcon provider={row?.provider ?? ""} size={12} />
          <span>{truncateName(row?.baseModel ?? payload.value, 14)}</span>
        </div>
      </foreignObject>
    </g>
  );
}

export function rowMap(rows: GroupedMetricRow[]) {
  return rows.reduce(
    (acc, row) => {
      acc[row.id] = row;
      return acc;
    },
    {} as Record<string, GroupedMetricRow>,
  );
}

export function paddedDomain(
  rows: GroupedMetricRow[],
  fallback: [number, number],
  options: { floor?: number; ceiling?: number; paddingRatio?: number } = {},
): [number, number] {
  if (rows.length === 0) return fallback;
  const min = Math.min(...rows.map((row) => row.minValue));
  const max = Math.max(...rows.map((row) => row.maxValue));
  const span = Math.max(max - min, Math.abs(max) * 0.08, 1);
  const padding = span * (options.paddingRatio ?? 0.12);
  const lower = Math.max(options.floor ?? -Infinity, min - padding);
  const upper = Math.min(options.ceiling ?? Infinity, max + padding);
  if (lower === upper) {
    return [Math.max(options.floor ?? -Infinity, lower - 1), upper + 1];
  }
  return [lower, upper];
}

export function formatCompactDecimal(value: number, maxFractionDigits = 2): string {
  return new Intl.NumberFormat("en-US", {
    minimumFractionDigits: 0,
    maximumFractionDigits: maxFractionDigits,
  }).format(value);
}

export const tooltipStyle = {
  background: "var(--card)",
  border: "2px solid var(--border)",
  borderRadius: 10,
  padding: "8px 12px",
  fontSize: 12,
  fontFamily: "var(--font-mono)",
  color: "var(--text-dim)",
};
