import { useMemo, useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { useNavigation } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { ArrowLeft, Check } from 'lucide-react-native';

import type { SettingsStackParamList } from '@/app/navigation/types';
import {
  defaultAppSettings,
  useAppSettingsStore,
  type DockSettings,
} from '@/shared/settings';
import { useAppTheme } from '@/shared/theme';
import { GlassSlider, GlassView } from '@/shared/ui';
import { DockIcon } from '@/widgets/dock/dock-icon';
import {
  CatalogBackdrop,
  CatalogScreenHeader,
  DemoButton,
  DemoSurface,
  catalogLayout,
} from '@/features/catalog';

const surfaceControls = [
  {
    key: 'opticalIntensity',
    label: 'Dock optical depth',
    description: 'Clear to regular native material depth.',
  },
  {
    key: 'transparency',
    label: 'Dock transparency',
    description: 'Controls how much page content remains visible.',
  },
  {
    key: 'surfaceLiquidity',
    label: 'Dock liquidity',
    description: 'Changes edge softness, radius and shadow spread.',
  },
  {
    key: 'backgroundOpacity',
    label: 'Dock background',
    description: 'Adds a stable neutral layer beneath native refraction.',
  },
] as const satisfies readonly DockControl[];

const blobControls = [
  {
    key: 'blobIntensity',
    label: 'Blob optical depth',
    description: 'Controls the selected-page material emphasis.',
  },
  {
    key: 'blobTransparency',
    label: 'Blob transparency',
    description: 'Reveals more or less of the dock underneath.',
  },
  {
    key: 'blobLiquidity',
    label: 'Blob liquidity',
    description: 'Changes the softness of the active indicator.',
  },
  {
    key: 'blobSize',
    label: 'Blob size',
    description: 'Controls the selected-page capsule width.',
  },
] as const satisfies readonly DockControl[];

type DockNumericKey = {
  [Key in keyof DockSettings]: DockSettings[Key] extends number ? Key : never;
}[keyof DockSettings];

type DockControl = Readonly<{
  key: DockNumericKey;
  label: string;
  description: string;
}>;

export function DockSettingsScreen() {
  const theme = useAppTheme();
  const insets = useSafeAreaInsets();
  const navigation =
    useNavigation<NativeStackNavigationProp<SettingsStackParamList>>();
  const persistedDock = useAppSettingsStore(state => state.settings.dock);
  const setDockSettings = useAppSettingsStore(state => state.setDockSettings);
  const [draft, setDraft] = useState<DockSettings>(persistedDock);
  const [applied, setApplied] = useState(false);
  const isDark =
    draft.tone === 'dark' || (draft.tone === 'adaptive' && theme.isDark);
  const tone = draft.tone === 'adaptive' ? 'theme' : draft.tone;
  const overlayAlpha = (draft.backgroundOpacity / 100) * 0.52;
  const previewDockStyle = {
    backgroundColor: isDark
      ? `rgba(3,3,5,${overlayAlpha})`
      : `rgba(255,255,255,${overlayAlpha})`,
    borderColor: isDark ? 'rgba(255,255,255,0.22)' : 'rgba(17,18,22,0.18)',
  };
  const changed = useMemo(
    () => JSON.stringify(draft) !== JSON.stringify(persistedDock),
    [draft, persistedDock],
  );

  const setValue = (key: DockNumericKey, value: number) => {
    setApplied(false);
    setDraft(current => ({ ...current, [key]: value }));
  };

  const apply = () => {
    setDockSettings(draft);
    setApplied(true);
  };

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
          description="Tune the dock and active-page blob, preview the result, then apply it."
          eyebrow="Navigation material"
          title="Dock settings"
          trailing={
            <Pressable
              accessibilityLabel="Back to settings"
              accessibilityRole="button"
              hitSlop={8}
              onPress={() => navigation.goBack()}
              style={styles.iconButton}
            >
              <GlassView
                interactive
                pointerEvents="none"
                style={StyleSheet.absoluteFill}
                variant="control"
              />
              <ArrowLeft color={theme.colors.text} size={21} />
            </Pressable>
          }
        />

        <DemoSurface
          title="Live preview"
          description="The real dock changes only after Apply."
        >
          <View
            style={[
              styles.previewBackdrop,
              { backgroundColor: theme.colors.canvasElevated },
            ]}
          >
            <View
              style={[
                styles.orb,
                styles.orbTop,
                { backgroundColor: theme.colors.text },
              ]}
            />
            <View
              style={[
                styles.orb,
                styles.orbBottom,
                { backgroundColor: theme.colors.textMuted },
              ]}
            />
            <GlassView
              materialSettings={draft}
              tone={tone}
              variant="floating"
              style={[styles.previewDock, previewDockStyle]}
            >
              {(
                ['home', 'palette', 'components', 'layout', 'settings'] as const
              ).map((icon, index) => {
                const selected = index === 2;
                const color = isDark ? '#FFFFFF' : '#111216';
                return (
                  <View key={icon} style={styles.previewSlot}>
                    {selected ? (
                      <GlassView
                        materialSettings={{
                          opticalIntensity: draft.blobIntensity,
                          transparency: draft.blobTransparency,
                          surfaceLiquidity: draft.blobLiquidity,
                        }}
                        tone={tone}
                        variant="control"
                        style={[
                          styles.previewBlob,
                          { width: `${draft.blobSize}%` },
                        ]}
                      />
                    ) : null}
                    <DockIcon
                      color={selected ? color : `${color}88`}
                      name={icon}
                      size={20}
                    />
                  </View>
                );
              })}
            </GlassView>
          </View>

          <View style={styles.toneRow}>
            {(['adaptive', 'light', 'dark'] as const).map(value => {
              const selected = draft.tone === value;
              return (
                <DemoButton
                  key={value}
                  accessibilityState={{ selected }}
                  label={value[0].toUpperCase() + value.slice(1)}
                  onPress={() => {
                    setApplied(false);
                    setDraft(current => ({ ...current, tone: value }));
                  }}
                  style={styles.toneButton}
                  variant={selected ? 'primary' : 'secondary'}
                />
              );
            })}
          </View>
        </DemoSurface>

        <ControlSection
          controls={surfaceControls}
          draft={draft}
          onChange={setValue}
          title="Dock surface"
        />
        <ControlSection
          controls={blobControls}
          draft={draft}
          onChange={setValue}
          title="Active-page blob"
        />

        <View style={styles.actionRow}>
          <DemoButton
            label="Reset preview"
            onPress={() => {
              setApplied(false);
              setDraft(defaultAppSettings.dock);
            }}
            style={styles.actionButton}
            variant="secondary"
          />
          <DemoButton
            disabled={!changed}
            label={applied ? 'Applied' : 'Apply dock'}
            onPress={apply}
            style={styles.actionButton}
          />
        </View>

        {applied ? (
          <View accessibilityLiveRegion="polite" style={styles.appliedRow}>
            <Check color={theme.colors.positive} size={18} />
            <Text
              style={[theme.typography.label, { color: theme.colors.text }]}
            >
              Dock material applied
            </Text>
          </View>
        ) : null}
      </ScrollView>
    </CatalogBackdrop>
  );
}

function ControlSection({
  title,
  controls,
  draft,
  onChange,
}: Readonly<{
  title: string;
  controls: readonly DockControl[];
  draft: DockSettings;
  onChange: (key: DockNumericKey, value: number) => void;
}>) {
  const theme = useAppTheme();
  return (
    <DemoSurface title={title}>
      {controls.map(control => (
        <View key={control.key} style={styles.control}>
          <View style={styles.controlHeader}>
            <View style={styles.flex}>
              <Text
                style={[theme.typography.body, { color: theme.colors.text }]}
              >
                {control.label}
              </Text>
              <Text style={[styles.caption, { color: theme.colors.textMuted }]}>
                {control.description}
              </Text>
            </View>
            <GlassView style={styles.valuePill} variant="control">
              <Text
                style={[theme.typography.label, { color: theme.colors.text }]}
              >
                {Math.round(draft[control.key])}%
              </Text>
            </GlassView>
          </View>
          <GlassSlider
            accessibilityLabel={control.label}
            onValueChange={value => onChange(control.key, value)}
            value={draft[control.key]}
          />
        </View>
      ))}
    </DemoSurface>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  iconButton: {
    alignItems: 'center',
    borderRadius: 18,
    height: 48,
    justifyContent: 'center',
    overflow: 'hidden',
    width: 48,
  },
  previewBackdrop: {
    borderRadius: 28,
    height: 180,
    justifyContent: 'flex-end',
    overflow: 'hidden',
    padding: 16,
  },
  orb: { borderRadius: 999, height: 120, position: 'absolute', width: 120 },
  orbTop: { opacity: 0.18, right: -18, top: -36 },
  orbBottom: { bottom: -48, left: 20, opacity: 0.16 },
  previewDock: {
    alignItems: 'center',
    borderRadius: 999,
    flexDirection: 'row',
    height: 62,
  },
  previewSlot: {
    alignItems: 'center',
    flex: 1,
    height: 56,
    justifyContent: 'center',
  },
  previewBlob: {
    alignSelf: 'center',
    borderRadius: 999,
    bottom: 1,
    position: 'absolute',
    top: 1,
  },
  toneRow: { flexDirection: 'row', gap: 8 },
  toneButton: { flex: 1, paddingHorizontal: 6 },
  control: { gap: 4 },
  controlHeader: { alignItems: 'flex-start', flexDirection: 'row', gap: 10 },
  caption: { fontSize: 13, lineHeight: 18, marginTop: 2 },
  valuePill: {
    alignItems: 'center',
    borderRadius: 17,
    justifyContent: 'center',
    minHeight: 34,
    minWidth: 54,
    paddingHorizontal: 8,
  },
  actionRow: { flexDirection: 'row', gap: 10 },
  actionButton: { flex: 1 },
  appliedRow: {
    alignItems: 'center',
    flexDirection: 'row',
    justifyContent: 'center',
    paddingBottom: 12,
  },
});
