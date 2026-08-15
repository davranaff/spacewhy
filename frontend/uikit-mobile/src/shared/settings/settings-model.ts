import type { ThemeMode } from '@/shared/theme/tokens';

export const APP_SETTINGS_VERSION = 1;

export interface GlassSettings {
  opticalIntensity: number;
  transparency: number;
  surfaceLiquidity: number;
}

export interface AppSettings {
  schemaVersion: typeof APP_SETTINGS_VERSION;
  themeMode: ThemeMode;
  locale: 'en' | 'ru' | 'uz';
  glass: GlassSettings;
}

export const defaultAppSettings: AppSettings = {
  schemaVersion: APP_SETTINGS_VERSION,
  themeMode: 'system',
  locale: 'en',
  glass: {
    opticalIntensity: 68,
    transparency: 56,
    surfaceLiquidity: 72,
  },
};

export function clampSettingValue(value: unknown, fallback: number): number {
  if (typeof value !== 'number' || !Number.isFinite(value)) {
    return fallback;
  }

  return Math.min(100, Math.max(0, Math.round(value)));
}

export function normalizeAppSettings(value: unknown): AppSettings {
  if (!value || typeof value !== 'object') {
    return defaultAppSettings;
  }

  const candidate = value as Partial<AppSettings>;
  const glass = candidate.glass ?? defaultAppSettings.glass;
  const themeMode = ['system', 'light', 'dark'].includes(
    candidate.themeMode ?? '',
  )
    ? candidate.themeMode!
    : defaultAppSettings.themeMode;
  const locale = ['en', 'ru', 'uz'].includes(candidate.locale ?? '')
    ? candidate.locale!
    : defaultAppSettings.locale;

  return {
    schemaVersion: APP_SETTINGS_VERSION,
    themeMode,
    locale,
    glass: {
      opticalIntensity: clampSettingValue(
        glass.opticalIntensity,
        defaultAppSettings.glass.opticalIntensity,
      ),
      transparency: clampSettingValue(
        glass.transparency,
        defaultAppSettings.glass.transparency,
      ),
      surfaceLiquidity: clampSettingValue(
        glass.surfaceLiquidity,
        defaultAppSettings.glass.surfaceLiquidity,
      ),
    },
  };
}
