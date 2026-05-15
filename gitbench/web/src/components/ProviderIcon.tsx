import type { ComponentType } from 'react';
import type { IconProps } from '@icons-pack/react-simple-icons';
import {
  SiAnthropic,
  SiGoogle,
  SiMeta,
  SiMistralai,
} from '@icons-pack/react-simple-icons';

// Map of lowercase provider slugs → Simple Icons component
const PROVIDER_ICON_MAP: Record<string, ComponentType<IconProps>> = {
  anthropic: SiAnthropic,
  google: SiGoogle,
  meta: SiMeta,
  mistral: SiMistralai,
  // openai, deepseek: not yet in simple-icons 13.x — fallback below
};

/** Derive a deterministic hue for a provider string (golden-angle spacing). */
function providerHue(provider: string): number {
  let h = 0;
  for (let i = 0; i < provider.length; i++) {
    h = (h * 31 + provider.charCodeAt(i)) & 0xffffffff;
  }
  return (h >>> 0) % 360;
}

const SIZE_REGEX = /^size-/;

interface ProviderIconProps {
  provider: string;
  size?: number;
}

export default function ProviderIcon({ provider, size = 16 }: ProviderIconProps) {
  const normalized = provider.toLowerCase();
  const IconComponent = PROVIDER_ICON_MAP[normalized];

  if (IconComponent) {
    // Filter out size-* classes that simple-icons adds
    const filtered: Record<string, string> = {};
    if (IconComponent.defaultProps) {
      for (const [k, v] of Object.entries(IconComponent.defaultProps as Record<string, unknown>)) {
        if (typeof v === 'string' && !SIZE_REGEX.test(k)) {
          filtered[k] = v;
        }
      }
    }
    return (
      <IconComponent
        size={size}
        color="default"
        {...filtered}
      />
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
