export type GlassValues = {
  glassIntensity: number;
  glassTransparency: number;
  glassLiquidity: number;
};

const clamp = (value: number) => Math.min(100, Math.max(0, value));

export function getGlassCssVars(values: GlassValues) {
  const intensity = clamp(values.glassIntensity) / 100;
  const transparency = clamp(values.glassTransparency) / 100;
  const liquidity = clamp(values.glassLiquidity) / 100;

  const blur = 4 + intensity * 20;
  const surfaceBlur = 3 + intensity * 11;
  const controlBlur = 2 + intensity * 8;
  const saturation = 100 + intensity * 32;
  const darkAlpha = 0.68 - transparency * 0.58;
  const lightAlpha = 0.96 - transparency * 0.58;
  const darkControlAlpha = darkAlpha * 0.82;
  const lightControlAlpha = lightAlpha * 0.72;
  const radius = 12 + liquidity * 15;
  const shadowBlur = 20 + liquidity * 30;
  const shadowOffset = 8 + liquidity * 12;
  const shadowAlphaDark = 0.16 + liquidity * 0.14;
  const shadowAlphaLight = 0.07 + liquidity * 0.07;
  const edgeAlphaDark = 0.07 + liquidity * 0.09;
  const edgeAlphaLight = 0.08 + liquidity * 0.05;

  return {
    '--spacewhy-glass-blur': `${blur.toFixed(1)}px`,
    '--spacewhy-glass-surface-blur': `${surfaceBlur.toFixed(1)}px`,
    '--spacewhy-glass-control-blur': `${controlBlur.toFixed(1)}px`,
    '--spacewhy-glass-alpha': darkAlpha.toFixed(3),
    '--spacewhy-glass-alpha-light': lightAlpha.toFixed(3),
    '--spacewhy-glass-control-alpha': darkControlAlpha.toFixed(3),
    '--spacewhy-glass-control-alpha-light': lightControlAlpha.toFixed(3),
    '--spacewhy-glass-intensity': intensity.toFixed(2),
    '--spacewhy-glass-liquid': liquidity.toFixed(2),
    '--spacewhy-glass-radius': `${radius.toFixed(1)}px`,
    '--spacewhy-glass-saturation': `${saturation.toFixed(0)}%`,
    '--spacewhy-glass-shadow-blur': `${shadowBlur.toFixed(1)}px`,
    '--spacewhy-glass-shadow-offset': `${shadowOffset.toFixed(1)}px`,
    '--spacewhy-glass-shadow-alpha-dark': shadowAlphaDark.toFixed(3),
    '--spacewhy-glass-shadow-alpha-light': shadowAlphaLight.toFixed(3),
    '--spacewhy-glass-edge-alpha-dark': edgeAlphaDark.toFixed(3),
    '--spacewhy-glass-edge-alpha-light': edgeAlphaLight.toFixed(3),
  } as const;
}

export function applyGlassCssVars(values: GlassValues) {
  const root = document.documentElement;

  Object.entries(getGlassCssVars(values)).forEach(([name, value]) => {
    root.style.setProperty(name, value);
  });
}
