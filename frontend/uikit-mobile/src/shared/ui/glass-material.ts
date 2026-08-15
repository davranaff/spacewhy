import type { AppTheme } from '@/shared/theme';

export type GlassVariant = 'surface' | 'control' | 'floating';

export interface GlassMaterialInput {
  variant: GlassVariant;
  opticalIntensity: number;
  transparency: number;
  surfaceLiquidity: number;
}

export interface GlassMaterial {
  blurAmount: number;
  borderRadius: number;
  borderColor: string;
  matteColor: string;
  nativeTintColor: string;
  reducedTransparencyColor: string;
  shadowOpacity: number;
  shadowRadius: number;
}

const variantDepth = {
  surface: 0,
  control: -3,
  floating: 5,
} as const;

function clamp(value: number): number {
  return Math.min(100, Math.max(0, value));
}

function rgba(red: number, green: number, blue: number, alpha: number): string {
  return `rgba(${red}, ${green}, ${blue}, ${alpha.toFixed(3)})`;
}

export function resolveGlassMaterial(
  theme: AppTheme,
  input: GlassMaterialInput,
): GlassMaterial {
  const intensity = clamp(input.opticalIntensity) / 100;
  const transparency = clamp(input.transparency) / 100;
  const liquidity = clamp(input.surfaceLiquidity) / 100;
  const depth = variantDepth[input.variant];
  const baseChannel = theme.isDark ? 255 : 18;
  const matteAlpha = theme.isDark
    ? 0.8 - transparency * 0.62
    : 0.94 - transparency * 0.52;
  const nativeTintAlpha = theme.isDark
    ? 0.34 - transparency * 0.29
    : 0.48 - transparency * 0.38;
  // Native iOS glass exposes discrete clear/regular optics. A continuous neutral
  // tint depth keeps the optical slider visibly progressive without changing alpha.
  const tintChannel = Math.round(
    theme.isDark ? 26 - intensity * 22 : 255 - intensity * 27,
  );

  return {
    blurAmount: Math.round(8 + intensity * 18 + depth),
    borderRadius: Math.round(14 + liquidity * 16 + depth * 0.4),
    borderColor: rgba(
      baseChannel,
      baseChannel,
      baseChannel,
      0.16 - liquidity * 0.08,
    ),
    matteColor: theme.isDark
      ? rgba(15, 16, 19, matteAlpha)
      : rgba(248, 249, 251, matteAlpha),
    nativeTintColor: rgba(
      tintChannel,
      tintChannel,
      tintChannel,
      nativeTintAlpha,
    ),
    reducedTransparencyColor: theme.colors.surface,
    shadowOpacity: theme.isDark
      ? 0.26 - liquidity * 0.1
      : 0.14 - liquidity * 0.07,
    shadowRadius: Math.round(10 + liquidity * 14 + Math.max(0, depth)),
  };
}
