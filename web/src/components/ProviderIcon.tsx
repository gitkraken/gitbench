import { PROVIDER_ICONS } from "@/lib/custom-provider-icons";
import { PROVIDER_COLORS, providerHue } from "@/lib/provider-colors";

interface ProviderIconProps {
  provider: string;
  size?: number;
}

export default function ProviderIcon({
  provider,
  size = 16,
}: ProviderIconProps) {
  const normalized = provider.toLowerCase();
  const IconComponent = PROVIDER_ICONS[normalized];

  if (IconComponent) {
    const color = PROVIDER_COLORS[normalized];
    const showBgCircle = size <= 14;

    return (
      <span
        style={{
          position: "relative",
          display: "inline-flex",
          alignItems: "center",
          justifyContent: "center",
          color: color ?? undefined,
        }}
      >
        {showBgCircle && (
          <span
            style={{
              position: "absolute",
              width: size + 4,
              height: size + 4,
              borderRadius: "50%",
              background: "rgba(255,255,255,0.08)",
            }}
          />
        )}
        <IconComponent width={size} height={size} aria-hidden="true" />
      </span>
    );
  }

  // Fallback: colored circle with first letter
  const hue = providerHue(normalized);
  const initial = normalized.charAt(0).toUpperCase();

  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      <circle cx="12" cy="12" r="12" fill={`hsl(${hue}, 55%, 45%)`} />
      <text
        x="12"
        y="16"
        textAnchor="middle"
        fill="white"
        fontSize="13"
        fontWeight="bold"
        fontFamily="system-ui, sans-serif"
      >
        {initial}
      </text>
    </svg>
  );
}
