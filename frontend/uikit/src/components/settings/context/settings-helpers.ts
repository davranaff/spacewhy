import { clampGlassValue } from 'src/theme/glass-tokens';

import type { SettingsValueProps } from '../types';

// ----------------------------------------------------------------------

const THEME_MODES = ['light', 'dark'] as const;
const THEME_DIRECTIONS = ['rtl', 'ltr'] as const;
const THEME_CONTRASTS = ['default', 'bold'] as const;
const THEME_LAYOUTS = ['vertical', 'horizontal', 'mini'] as const;
const THEME_COLOR_PRESETS = ['default', 'cyan', 'purple', 'blue', 'orange', 'red'] as const;

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === 'object' && value !== null && !Array.isArray(value);

const selectBoolean = (value: unknown, fallback: boolean) =>
  typeof value === 'boolean' ? value : fallback;

const selectOption = <Value extends string>(
  value: unknown,
  options: readonly Value[],
  fallback: Value
) =>
  typeof value === 'string' && options.includes(value as Value) ? (value as Value) : fallback;

const selectGlassValue = (value: unknown, fallback: number) =>
  typeof value === 'number' ? clampGlassValue(value) : clampGlassValue(fallback);

/**
 * Restores persisted settings without allowing stale, malformed, or partial values
 * to break newly introduced settings.
 */
export function mergeSettings(
  defaultSettings: SettingsValueProps,
  persistedSettings: unknown
): SettingsValueProps {
  const persisted = isRecord(persistedSettings) ? persistedSettings : {};

  return {
    themeStretch: selectBoolean(persisted.themeStretch, defaultSettings.themeStretch),
    themeMode: selectOption(persisted.themeMode, THEME_MODES, defaultSettings.themeMode),
    themeDirection: selectOption(
      persisted.themeDirection,
      THEME_DIRECTIONS,
      defaultSettings.themeDirection
    ),
    themeContrast: selectOption(
      persisted.themeContrast,
      THEME_CONTRASTS,
      defaultSettings.themeContrast
    ),
    themeLayout: selectOption(persisted.themeLayout, THEME_LAYOUTS, defaultSettings.themeLayout),
    themeColorPresets: selectOption(
      persisted.themeColorPresets,
      THEME_COLOR_PRESETS,
      defaultSettings.themeColorPresets
    ),
    glassIntensity: selectGlassValue(
      persisted.glassIntensity,
      defaultSettings.glassIntensity
    ),
    glassTransparency: selectGlassValue(
      persisted.glassTransparency,
      defaultSettings.glassTransparency
    ),
    glassLiquidity: selectGlassValue(
      persisted.glassLiquidity,
      defaultSettings.glassLiquidity
    ),
  };
}

export function updateSettingsValue(
  defaultSettings: SettingsValueProps,
  currentSettings: unknown,
  name: string,
  value: string | boolean | number
) {
  const current = isRecord(currentSettings) ? currentSettings : {};

  return mergeSettings(defaultSettings, { ...current, [name]: value });
}
