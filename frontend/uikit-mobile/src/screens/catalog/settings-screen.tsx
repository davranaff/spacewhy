import { useEffect, useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import Slider from '@react-native-community/slider';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { Monitor, Moon, RotateCcw, Sparkles, Sun } from 'lucide-react-native';

import { useAppSettingsStore, type GlassSettings } from '@/shared/settings';
import { useAppTheme, type ThemeMode } from '@/shared/theme';
import { GlassView } from '@/shared/ui/glass-view';
import {
  CatalogBackdrop,
  CatalogScreenHeader,
  DemoButton,
  DemoSurface,
  catalogLayout,
} from '@/features/catalog';

const themeModes = [
  { value: 'system', label: 'System', Icon: Monitor },
  { value: 'light', label: 'Light', Icon: Sun },
  { value: 'dark', label: 'Dark', Icon: Moon },
] as const satisfies readonly {
  value: ThemeMode;
  label: string;
  Icon: typeof Monitor;
}[];

const glassControls = [
  {
    key: 'opticalIntensity',
    label: 'Optical intensity',
    description: 'Changes native material depth and fallback blur.',
    start: 'Clear',
    end: 'Deep',
  },
  {
    key: 'transparency',
    label: 'Transparency',
    description: 'Higher values reveal more of the backdrop.',
    start: 'Solid',
    end: 'Clear',
  },
  {
    key: 'surfaceLiquidity',
    label: 'Surface liquidity',
    description: 'Changes radius, edge softness and shadow spread.',
    start: 'Rigid',
    end: 'Fluid',
  },
] as const satisfies readonly {
  key: keyof GlassSettings;
  label: string;
  description: string;
  start: string;
  end: string;
}[];

export function SettingsScreen() {
  const theme = useAppTheme();
  const insets = useSafeAreaInsets();
  const settings = useAppSettingsStore(state => state.settings);
  const setThemeMode = useAppSettingsStore(state => state.setThemeMode);
  const setGlassSettings = useAppSettingsStore(state => state.setGlassSettings);
  const setLocale = useAppSettingsStore(state => state.setLocale);
  const resetSettings = useAppSettingsStore(state => state.resetSettings);
  const [draftGlass, setDraftGlass] = useState(settings.glass);

  useEffect(() => setDraftGlass(settings.glass), [settings.glass]);

  return (
    <CatalogBackdrop>
      <ScrollView
        contentContainerStyle={[
          catalogLayout.content,
          { paddingTop: Math.max(insets.top, 12) + 4 },
        ]}
        showsVerticalScrollIndicator={false}
      >
        <CatalogScreenHeader
          description="Theme, language and truthful liquid-glass material controls."
          title="Settings"
          trailing={
            <Pressable
              accessibilityRole="button"
              accessibilityLabel="Reset all settings"
              hitSlop={8}
              onPress={resetSettings}
              style={[
                styles.resetButton,
                {
                  borderColor: theme.colors.border,
                  backgroundColor: theme.colors.surface,
                },
              ]}
            >
              <RotateCcw color={theme.colors.text} size={19} />
            </Pressable>
          }
        />

        <DemoSurface
          title="Appearance"
          description="Choose a fixed theme or follow the operating system."
        >
          <View style={styles.modeRow}>
            {themeModes.map(({ value, label, Icon }) => {
              const selected = settings.themeMode === value;
              return (
                <Pressable
                  key={value}
                  accessibilityRole="radio"
                  accessibilityLabel={`${label} theme`}
                  accessibilityState={{ selected }}
                  onPress={() => setThemeMode(value)}
                  style={[
                    styles.modeButton,
                    {
                      backgroundColor: selected
                        ? theme.colors.accent
                        : theme.colors.surfaceElevated,
                      borderColor: selected
                        ? theme.colors.accent
                        : theme.colors.border,
                    },
                  ]}
                >
                  <Icon
                    color={
                      selected ? theme.colors.accentContrast : theme.colors.text
                    }
                    size={21}
                  />
                  <Text
                    style={[
                      theme.typography.label,
                      {
                        color: selected
                          ? theme.colors.accentContrast
                          : theme.colors.text,
                      },
                    ]}
                  >
                    {label}
                  </Text>
                </Pressable>
              );
            })}
          </View>
        </DemoSurface>

        <DemoSurface
          title="Live material"
          description="Each control changes one visible dimension of the glass."
        >
          <View
            style={[
              styles.previewBackdrop,
              { backgroundColor: theme.colors.canvasElevated },
            ]}
          >
            <View
              style={[
                styles.previewOrb,
                styles.previewOrbOne,
                { backgroundColor: theme.colors.accent },
              ]}
            />
            <View
              style={[
                styles.previewOrb,
                styles.previewOrbTwo,
                { backgroundColor: theme.colors.positive },
              ]}
            />
            <GlassView
              materialSettings={draftGlass}
              variant="floating"
              style={styles.liveGlass}
            >
              <Sparkles color={theme.colors.text} size={24} />
              <View style={styles.flex}>
                <Text
                  style={[
                    theme.typography.title,
                    styles.liveTitle,
                    { color: theme.colors.text },
                  ]}
                >
                  Spacewhy glass
                </Text>
                <Text
                  style={[
                    styles.previewCaption,
                    { color: theme.colors.textMuted },
                  ]}
                >
                  Native material preview
                </Text>
              </View>
            </GlassView>
          </View>

          {glassControls.map(control => (
            <View key={control.key} style={styles.controlGroup}>
              <View style={styles.controlHeading}>
                <View style={styles.flex}>
                  <Text
                    style={[
                      theme.typography.body,
                      styles.controlLabel,
                      { color: theme.colors.text },
                    ]}
                  >
                    {control.label}
                  </Text>
                  <Text
                    style={[
                      styles.controlDescription,
                      { color: theme.colors.textMuted },
                    ]}
                  >
                    {control.description}
                  </Text>
                </View>
                <View
                  style={[
                    styles.valuePill,
                    {
                      borderColor: theme.colors.border,
                      backgroundColor: theme.colors.surfaceElevated,
                    },
                  ]}
                >
                  <Text
                    accessibilityLiveRegion="polite"
                    style={[
                      theme.typography.label,
                      { color: theme.colors.text },
                    ]}
                  >
                    {Math.round(draftGlass[control.key])}%
                  </Text>
                </View>
              </View>
              <Slider
                accessibilityLabel={control.label}
                accessibilityValue={{
                  min: 0,
                  max: 100,
                  now: Math.round(draftGlass[control.key]),
                  text: `${Math.round(draftGlass[control.key])} percent`,
                }}
                maximumTrackTintColor={theme.colors.border}
                maximumValue={100}
                minimumTrackTintColor={theme.colors.accent}
                minimumValue={0}
                onSlidingComplete={value =>
                  setGlassSettings({ [control.key]: value })
                }
                onValueChange={value =>
                  setDraftGlass(current => ({
                    ...current,
                    [control.key]: value,
                  }))
                }
                step={1}
                thumbTintColor={theme.colors.text}
                value={draftGlass[control.key]}
              />
              <View style={styles.rangeLabels}>
                <Text
                  style={[
                    styles.previewCaption,
                    { color: theme.colors.textMuted },
                  ]}
                >
                  {control.start}
                </Text>
                <Text
                  style={[
                    styles.previewCaption,
                    { color: theme.colors.textMuted },
                  ]}
                >
                  {control.end}
                </Text>
              </View>
            </View>
          ))}
        </DemoSurface>

        <DemoSurface
          title="Language"
          description="The app shell is ready for localized catalog copy."
        >
          <View style={styles.languageRow}>
            {(['en', 'ru', 'uz'] as const).map(locale => {
              const selected = settings.locale === locale;
              return (
                <DemoButton
                  key={locale}
                  accessibilityState={{ selected }}
                  label={locale.toLocaleUpperCase()}
                  onPress={() => setLocale(locale)}
                  style={styles.languageButton}
                  variant={selected ? 'primary' : 'secondary'}
                />
              );
            })}
          </View>
        </DemoSurface>
      </ScrollView>
    </CatalogBackdrop>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  resetButton: {
    width: 48,
    height: 48,
    borderRadius: 17,
    borderWidth: StyleSheet.hairlineWidth,
    alignItems: 'center',
    justifyContent: 'center',
  },
  modeRow: { flexDirection: 'row', gap: 8 },
  modeButton: {
    flex: 1,
    minHeight: 70,
    borderRadius: 18,
    borderWidth: StyleSheet.hairlineWidth,
    alignItems: 'center',
    justifyContent: 'center',
    gap: 7,
  },
  previewBackdrop: {
    height: 180,
    borderRadius: 24,
    overflow: 'hidden',
    alignItems: 'center',
    justifyContent: 'center',
  },
  previewOrb: {
    position: 'absolute',
    width: 110,
    height: 110,
    borderRadius: 55,
    opacity: 0.58,
  },
  previewOrbOne: { top: -22, right: -8 },
  previewOrbTwo: { bottom: -36, left: -20, opacity: 0.34 },
  liveGlass: {
    width: '78%',
    minHeight: 86,
    borderRadius: 28,
    paddingHorizontal: 18,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  liveTitle: { fontSize: 17, lineHeight: 22 },
  previewCaption: { fontSize: 12, lineHeight: 16 },
  controlGroup: { gap: 6, paddingTop: 4 },
  controlHeading: { flexDirection: 'row', alignItems: 'flex-start', gap: 10 },
  controlLabel: { fontWeight: '600' },
  controlDescription: { fontSize: 13, lineHeight: 18, marginTop: 2 },
  valuePill: {
    minWidth: 52,
    minHeight: 34,
    borderRadius: 17,
    borderWidth: StyleSheet.hairlineWidth,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 9,
  },
  rangeLabels: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  languageRow: { flexDirection: 'row', gap: 8 },
  languageButton: { flex: 1, paddingHorizontal: 8 },
});
