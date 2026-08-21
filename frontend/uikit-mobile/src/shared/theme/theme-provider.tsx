import {
  createContext,
  useContext,
  useMemo,
  type PropsWithChildren,
} from 'react';
import { useColorScheme } from 'react-native';

import { useAppSettingsStore } from '@/shared/settings';

import {
  createAppTheme,
  type AppTheme,
  type ResolvedThemeMode,
} from './tokens';

const AppThemeContext = createContext<AppTheme | null>(null);

export function AppThemeProvider({ children }: PropsWithChildren) {
  const systemMode = useColorScheme();
  const preferredMode = useAppSettingsStore(state => state.settings.themeMode);
  const resolvedMode: ResolvedThemeMode =
    preferredMode === 'system'
      ? systemMode === 'light'
        ? 'light'
        : 'dark'
      : preferredMode;
  const theme = useMemo(() => createAppTheme(resolvedMode), [resolvedMode]);

  return (
    <AppThemeContext.Provider value={theme}>
      {children}
    </AppThemeContext.Provider>
  );
}

export function useAppTheme(): AppTheme {
  const theme = useContext(AppThemeContext);

  if (!theme) {
    throw new Error('useAppTheme must be used inside AppThemeProvider');
  }

  return theme;
}
