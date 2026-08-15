import AsyncStorage from '@react-native-async-storage/async-storage';
import { create } from 'zustand';
import { createJSONStorage, persist } from 'zustand/middleware';

import {
  APP_SETTINGS_VERSION,
  defaultAppSettings,
  normalizeAppSettings,
  type AppSettings,
  type GlassSettings,
} from './settings-model';

const APP_SETTINGS_STORAGE_KEY = 'spacewhy:uikit:settings';

interface AppSettingsStore {
  settings: AppSettings;
  hasHydrated: boolean;
  setThemeMode: (themeMode: AppSettings['themeMode']) => void;
  setLocale: (locale: AppSettings['locale']) => void;
  setGlassSettings: (glass: Partial<GlassSettings>) => void;
  resetSettings: () => void;
  markHydrated: () => void;
}

export const useAppSettingsStore = create<AppSettingsStore>()(
  persist(
    set => ({
      settings: defaultAppSettings,
      hasHydrated: false,
      setThemeMode: themeMode =>
        set(state => ({
          settings: normalizeAppSettings({ ...state.settings, themeMode }),
        })),
      setLocale: locale =>
        set(state => ({
          settings: normalizeAppSettings({ ...state.settings, locale }),
        })),
      setGlassSettings: glass =>
        set(state => ({
          settings: normalizeAppSettings({
            ...state.settings,
            glass: { ...state.settings.glass, ...glass },
          }),
        })),
      resetSettings: () => set({ settings: defaultAppSettings }),
      markHydrated: () => set({ hasHydrated: true }),
    }),
    {
      name: APP_SETTINGS_STORAGE_KEY,
      version: APP_SETTINGS_VERSION,
      storage: createJSONStorage(() => AsyncStorage),
      partialize: state => ({ settings: state.settings } as AppSettingsStore),
      migrate: persistedState =>
        ({
          settings: normalizeAppSettings(
            (persistedState as Partial<AppSettingsStore>)?.settings,
          ),
        } as AppSettingsStore),
      merge: (persistedState, currentState) => ({
        ...currentState,
        settings: normalizeAppSettings(
          (persistedState as Partial<AppSettingsStore>)?.settings,
        ),
      }),
      onRehydrateStorage: () => state => state?.markHydrated(),
    },
  ),
);
