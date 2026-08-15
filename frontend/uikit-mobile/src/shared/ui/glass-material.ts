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

export function resolveGlassEffect(
  opticalIntensity: number,
): 'clear' | 'regular' {
  return clamp(opticalIntensity) >= 78 ? 'regular' : 'clear';
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
  const baseChannel = theme.isDark ? 255 : 17;
  const matteAlpha = theme.isDark
    ? 0.46 - transparency * 0.3
    : 0.42 - transparency * 0.28;
  // iOS 26 exposes clear/regular as discrete optics. Tint strength therefore
  // carries the continuous part of optical depth while transparency remains an
  // independent background-reveal axis.
  const nativeTintAlpha = theme.isDark
    ? 0.18 - transparency * 0.1 + intensity * 0.03
    : 0.16 - transparency * 0.1 + intensity * 0.08;

  return {
    blurAmount: Math.round(8 + intensity * 18 + depth),
    borderRadius: Math.round(14 + liquidity * 16 + depth * 0.4),
    borderColor: rgba(
      baseChannel,
      baseChannel,
      baseChannel,
      0.22 - liquidity * 0.08,
    ),
    matteColor: theme.isDark
      ? rgba(15, 16, 19, matteAlpha)
      : rgba(255, 255, 255, matteAlpha),
    nativeTintColor: rgba(
      theme.isDark ? 8 : 255,
      theme.isDark ? 8 : 255,
      theme.isDark ? 10 : 255,
      nativeTintAlpha,
    ),
    reducedTransparencyColor: theme.colors.surface,
    shadowOpacity: theme.isDark
      ? 0.26 - liquidity * 0.1
      : 0.14 - liquidity * 0.07,
    shadowRadius: Math.round(10 + liquidity * 14 + Math.max(0, depth)),
  };
}
