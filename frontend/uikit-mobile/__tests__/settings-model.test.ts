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
      glass: {
        opticalIntensity: 100,
        transparency: 0,
        surfaceLiquidity: defaultAppSettings.glass.surfaceLiquidity,
      },
    });
  });
});
