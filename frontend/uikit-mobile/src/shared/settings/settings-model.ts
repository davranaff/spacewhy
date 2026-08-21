import type { ThemeMode } from '@/shared/theme/tokens';

export const APP_SETTINGS_VERSION = 2;

export interface GlassSettings {
  opticalIntensity: number;
  transparency: number;
  surfaceLiquidity: number;
}

export interface DockSettings extends GlassSettings {
  tone: 'adaptive' | 'light' | 'dark';
  backgroundOpacity: number;
  blobIntensity: number;
  blobTransparency: number;
  blobLiquidity: number;
  blobSize: number;
}

export interface AppSettings {
  schemaVersion: typeof APP_SETTINGS_VERSION;
  themeMode: ThemeMode;
  locale: 'en' | 'ru' | 'uz';
  glass: GlassSettings;
  dock: DockSettings;
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
  dock: {
    tone: 'adaptive',
    opticalIntensity: 74,
    transparency: 70,
    surfaceLiquidity: 100,
    backgroundOpacity: 12,
    blobIntensity: 68,
    blobTransparency: 74,
    blobLiquidity: 100,
    blobSize: 82,
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
  const dock = candidate.dock ?? defaultAppSettings.dock;
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
    dock: {
      tone: ['adaptive', 'light', 'dark'].includes(dock.tone ?? '')
        ? dock.tone
        : defaultAppSettings.dock.tone,
      opticalIntensity: clampSettingValue(
        dock.opticalIntensity,
        defaultAppSettings.dock.opticalIntensity,
      ),
      transparency: clampSettingValue(
        dock.transparency,
        defaultAppSettings.dock.transparency,
      ),
      surfaceLiquidity: clampSettingValue(
        dock.surfaceLiquidity,
        defaultAppSettings.dock.surfaceLiquidity,
      ),
      backgroundOpacity: clampSettingValue(
        dock.backgroundOpacity,
        defaultAppSettings.dock.backgroundOpacity,
      ),
      blobIntensity: clampSettingValue(
        dock.blobIntensity,
        defaultAppSettings.dock.blobIntensity,
      ),
      blobTransparency: clampSettingValue(
        dock.blobTransparency,
        defaultAppSettings.dock.blobTransparency,
      ),
      blobLiquidity: clampSettingValue(
        dock.blobLiquidity,
        defaultAppSettings.dock.blobLiquidity,
      ),
      blobSize: clampSettingValue(
        dock.blobSize,
        defaultAppSettings.dock.blobSize,
      ),
    },
  };
}
