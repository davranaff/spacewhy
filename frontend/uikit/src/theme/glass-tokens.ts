export type GlassValues = {
  glassIntensity: number;
  glassTransparency: number;
  glassLiquidity: number;
};

export const clampGlassValue = (value: number) => {
  if (!Number.isFinite(value)) {
    return value === Number.POSITIVE_INFINITY ? 100 : 0;
  }

  return Math.min(100, Math.max(0, value));
};

const interpolate = (min: number, max: number, progress: number) =>
  min + (max - min) * progress;

export function getGlassCssVars(values: GlassValues) {
  const intensity = clampGlassValue(values.glassIntensity) / 100;
  const transparency = clampGlassValue(values.glassTransparency) / 100;
  const liquidity = clampGlassValue(values.glassLiquidity) / 100;

  // Optical intensity controls only the optical stack: blur, saturation and depth.
  const blur = interpolate(8, 28, intensity);
  const surfaceBlur = interpolate(4, 18, intensity);
  const controlBlur = interpolate(2, 12, intensity);
  const saturation = interpolate(100, 138, intensity);

  // Transparency exposes the scene without making labels or borders transparent.
  const darkAlpha = interpolate(0.78, 0.12, transparency);
  const lightAlpha = interpolate(0.92, 0.38, transparency);
  const darkFloatingAlpha = Math.min(0.86, darkAlpha + 0.08);
  const lightFloatingAlpha = Math.min(0.96, lightAlpha + 0.04);
  const darkControlAlpha = Math.min(0.82, darkAlpha + 0.06);
  const lightControlAlpha = Math.min(0.94, lightAlpha + 0.02);

  // Liquidity changes the edge character, not the whole product geometry.
  const radiusScale = interpolate(0.9, 1.12, liquidity);
  const floatingRadius = 24 * radiusScale;
  const surfaceRadius = 18 * radiusScale;
  const controlRadius = 12 * radiusScale;
  const shadowBlur = interpolate(18, 42, liquidity);
  const shadowOffset = interpolate(8, 16, liquidity);
  const shadowSpread = interpolate(0, 5, liquidity);
  const shadowAlphaDark = interpolate(0.24, 0.16, liquidity);
  const shadowAlphaLight = interpolate(0.12, 0.07, liquidity);
  const edgeAlphaDark = interpolate(0.16, 0.08, liquidity);
  const edgeAlphaLight = interpolate(0.18, 0.1, liquidity);
  const motionDuration = interpolate(150, 230, liquidity);

  return {
    '--spacewhy-glass-blur': `${blur.toFixed(1)}px`,
    '--spacewhy-glass-surface-blur': `${surfaceBlur.toFixed(1)}px`,
    '--spacewhy-glass-control-blur': `${controlBlur.toFixed(1)}px`,
    '--spacewhy-glass-alpha': darkAlpha.toFixed(3),
    '--spacewhy-glass-alpha-light': lightAlpha.toFixed(3),
    '--spacewhy-glass-floating-alpha': darkFloatingAlpha.toFixed(3),
    '--spacewhy-glass-floating-alpha-light': lightFloatingAlpha.toFixed(3),
    '--spacewhy-glass-control-alpha': darkControlAlpha.toFixed(3),
    '--spacewhy-glass-control-alpha-light': lightControlAlpha.toFixed(3),
    '--spacewhy-glass-intensity': intensity.toFixed(2),
    '--spacewhy-glass-liquid': liquidity.toFixed(2),
    '--spacewhy-glass-radius': `${surfaceRadius.toFixed(1)}px`,
    '--spacewhy-glass-floating-radius': `${floatingRadius.toFixed(1)}px`,
    '--spacewhy-glass-surface-radius': `${surfaceRadius.toFixed(1)}px`,
    '--spacewhy-glass-control-radius': `${controlRadius.toFixed(1)}px`,
    '--spacewhy-glass-saturation': `${saturation.toFixed(0)}%`,
    '--spacewhy-glass-shadow-blur': `${shadowBlur.toFixed(1)}px`,
    '--spacewhy-glass-shadow-offset': `${shadowOffset.toFixed(1)}px`,
    '--spacewhy-glass-shadow-spread': `${shadowSpread.toFixed(1)}px`,
    '--spacewhy-glass-shadow-alpha-dark': shadowAlphaDark.toFixed(3),
    '--spacewhy-glass-shadow-alpha-light': shadowAlphaLight.toFixed(3),
    '--spacewhy-glass-edge-alpha-dark': edgeAlphaDark.toFixed(3),
    '--spacewhy-glass-edge-alpha-light': edgeAlphaLight.toFixed(3),
    '--spacewhy-glass-motion-duration': `${motionDuration.toFixed(0)}ms`,
  } as const;
}

export function applyGlassCssVars(values: GlassValues) {
  if (typeof document === 'undefined') {
    return;
  }

  const root = document.documentElement;

  Object.entries(getGlassCssVars(values)).forEach(([name, value]) => {
    root.style.setProperty(name, value);
  });
}
