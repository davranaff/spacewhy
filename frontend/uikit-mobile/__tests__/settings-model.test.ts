import {
  APP_SETTINGS_VERSION,
  defaultAppSettings,
  normalizeAppSettings,
} from '@/shared/settings/settings-model';

describe('normalizeAppSettings', () => {
  it('restores defaults for malformed persisted data', () => {
    expect(normalizeAppSettings(null)).toEqual(defaultAppSettings);
    expect(normalizeAppSettings('invalid')).toEqual(defaultAppSettings);
  });

  it('migrates partial data and clamps glass controls', () => {
    expect(
      normalizeAppSettings({
        themeMode: 'light',
        locale: 'uz',
        glass: {
          opticalIntensity: 140,
          transparency: -20,
          surfaceLiquidity: Number.NaN,
        },
      }),
    ).toEqual({
      schemaVersion: APP_SETTINGS_VERSION,
      themeMode: 'light',
      locale: 'uz',
      dock: defaultAppSettings.dock,
      glass: {
        opticalIntensity: 100,
        transparency: 0,
        surfaceLiquidity: defaultAppSettings.glass.surfaceLiquidity,
      },
    });
  });

  it('normalizes persisted dock material independently', () => {
    const settings = normalizeAppSettings({
      dock: {
        ...defaultAppSettings.dock,
        tone: 'neon',
        backgroundOpacity: -5,
        blobSize: 130,
      },
    });

    expect(settings.dock.tone).toBe('adaptive');
    expect(settings.dock.backgroundOpacity).toBe(0);
    expect(settings.dock.blobSize).toBe(100);
  });
});
