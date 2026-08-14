'use client';

import merge from 'lodash/merge';
import { useMemo } from 'react';
// @mui
import CssBaseline from '@mui/material/CssBaseline';
import GlobalStyles from '@mui/material/GlobalStyles';
import { createTheme, ThemeProvider as MuiThemeProvider, ThemeOptions } from '@mui/material/styles';
// locales
import { useLocales } from 'src/locales';
// components
import { useSettingsContext } from 'src/components/settings';
// system
import { palette } from './palette';
import { shadows } from './shadows';
import { typography } from './typography';
import { customShadows } from './custom-shadows';
import { componentsOverrides } from './overrides';
// options
import { presets } from './options/presets';
import { darkMode } from './options/dark-mode';
import { contrast } from './options/contrast';
import RTL, { direction } from './options/right-to-left';
import { getGlassCssVars } from './glass-tokens';

// ----------------------------------------------------------------------

type Props = {
  children: React.ReactNode;
};

export default function ThemeProvider({ children }: Props) {
  const { currentLang } = useLocales();

  const settings = useSettingsContext();

  const glassIntensity = settings.glassIntensity ?? 78;

  const glassTransparency = settings.glassTransparency ?? 58;

  const glassLiquidity = settings.glassLiquidity ?? 82;

  const darkModeOption = useMemo(() => darkMode(settings.themeMode), [settings.themeMode]);

  const presetsOption = useMemo(
    () => presets(settings.themeColorPresets),
    [settings.themeColorPresets]
  );

  const contrastOption = useMemo(
    () => contrast(settings.themeContrast === 'bold', settings.themeMode),
    [settings.themeContrast, settings.themeMode]
  );

  const directionOption = useMemo(
    () => direction(settings.themeDirection),
    [settings.themeDirection]
  );

  const baseOption = useMemo(
    () => ({
      palette: palette('light'),
      shadows: shadows('light'),
      customShadows: customShadows('light'),
      typography,
      shape: { borderRadius: 12 },
    }),
    []
  );

  const memoizedValue = useMemo(
    () =>
      merge(
        {},
        // Base
        baseOption,
        // Direction: remove if not in use
        directionOption,
        // Dark mode: remove if not in use
        darkModeOption,
        // Presets: remove if not in use
        presetsOption,
        // Contrast: remove if not in use
        contrastOption.theme
      ),
    [baseOption, directionOption, darkModeOption, presetsOption, contrastOption.theme]
  );

  const theme = useMemo(() => {
    const nextTheme = createTheme(memoizedValue as ThemeOptions);

    nextTheme.components = merge(componentsOverrides(nextTheme), contrastOption.components);

    return nextTheme;
  }, [contrastOption.components, memoizedValue]);

  const themeWithLocale = useMemo(
    () => createTheme(theme, currentLang.systemValue),
    [currentLang.systemValue, theme]
  );

  const glassCssVars = useMemo(
    () =>
      getGlassCssVars({
        glassIntensity,
        glassTransparency,
        glassLiquidity,
      }),
    [glassIntensity, glassLiquidity, glassTransparency]
  );

  return (
    <MuiThemeProvider theme={themeWithLocale}>
      <GlobalStyles
        styles={{
          ':root': glassCssVars,
        }}
      />
      <RTL themeDirection={settings.themeDirection}>
        <CssBaseline />
        {children}
      </RTL>
    </MuiThemeProvider>
  );
}
