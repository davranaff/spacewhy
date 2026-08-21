import assert from 'node:assert/strict';
import test from 'node:test';

import {
  mergeSettings,
  updateSettingsValue,
} from 'src/components/settings/context/settings-helpers';
import type { SettingsValueProps } from 'src/components/settings/types';
import { parseStoredValue } from 'src/hooks/use-local-storage';

const defaults: SettingsValueProps = {
  themeStretch: false,
  themeMode: 'dark',
  themeDirection: 'ltr',
  themeContrast: 'default',
  themeLayout: 'vertical',
  themeColorPresets: 'default',
  glassIntensity: 69,
  glassTransparency: 56,
  glassLiquidity: 80,
};

test('mergeSettings fills fields that are absent from legacy persisted settings', () => {
  const legacySettings = {
    themeStretch: true,
    themeMode: 'light',
    themeDirection: 'rtl',
    themeContrast: 'bold',
    themeLayout: 'mini',
    themeColorPresets: 'cyan',
  };

  assert.deepEqual(mergeSettings(defaults, legacySettings), {
    ...legacySettings,
    glassIntensity: defaults.glassIntensity,
    glassTransparency: defaults.glassTransparency,
    glassLiquidity: defaults.glassLiquidity,
  });
});

test('mergeSettings rejects malformed values and clamps persisted glass controls', () => {
  const merged = mergeSettings(defaults, {
    themeStretch: 'yes',
    themeMode: 'auto',
    themeDirection: 'sideways',
    themeContrast: null,
    themeLayout: 2,
    themeColorPresets: 'green',
    glassIntensity: -20,
    glassTransparency: 160,
    glassLiquidity: Number.NaN,
  });

  assert.deepEqual(merged, {
    ...defaults,
    glassIntensity: 0,
    glassTransparency: 100,
    glassLiquidity: 0,
  });
});

test('updateSettingsValue returns a normalized immutable settings object', () => {
  const current = { ...defaults };
  const updated = updateSettingsValue(defaults, current, 'glassIntensity', 120);

  assert.notEqual(updated, current);
  assert.equal(current.glassIntensity, defaults.glassIntensity);
  assert.equal(updated.glassIntensity, 100);
});

test('parseStoredValue restores valid JSON and safely falls back for invalid storage', () => {
  assert.deepEqual(parseStoredValue('{"themeMode":"light"}', defaults), {
    themeMode: 'light',
  });
  assert.equal(parseStoredValue('not-json', defaults), defaults);
  assert.equal(parseStoredValue(null, defaults), defaults);
});
