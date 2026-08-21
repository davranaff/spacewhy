import { useEffect, type PropsWithChildren } from 'react';
import { I18nextProvider } from 'react-i18next';
import { StatusBar, StyleSheet } from 'react-native';
import { GestureHandlerRootView } from 'react-native-gesture-handler';
import { SafeAreaProvider } from 'react-native-safe-area-context';

import { i18n } from '@/shared/i18n/i18n';
import { useAppSettingsStore } from '@/shared/settings';
import { AppThemeProvider, useAppTheme } from '@/shared/theme';

function AppStatusBar() {
  const theme = useAppTheme();

  return (
    <StatusBar
      backgroundColor="transparent"
      barStyle={theme.isDark ? 'light-content' : 'dark-content'}
      translucent
    />
  );
}

function AppLocaleSync() {
  const locale = useAppSettingsStore(state => state.settings.locale);

  useEffect(() => {
    i18n.changeLanguage(locale).catch(() => undefined);
  }, [locale]);

  return null;
}

export function AppProviders({ children }: PropsWithChildren) {
  return (
    <GestureHandlerRootView style={styles.root}>
      <SafeAreaProvider>
        <I18nextProvider i18n={i18n}>
          <AppThemeProvider>
            <AppStatusBar />
            <AppLocaleSync />
            {children}
          </AppThemeProvider>
        </I18nextProvider>
      </SafeAreaProvider>
    </GestureHandlerRootView>
  );
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
  },
});
