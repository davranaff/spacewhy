import { useState } from 'react';
import { Pressable, StyleSheet, Switch, Text, View } from 'react-native';
import { Bell, Moon, UserRound } from 'lucide-react-native';

import {
  ShowcaseHeader,
  ShowcasePage,
} from '@/features/showcase/components/showcase-primitives';
import { useAppSettingsStore } from '@/shared/settings';
import { useAppTheme } from '@/shared/theme';
import { GlassSlider, GlassView } from '@/shared/ui';

export function ShowcaseProfileSettingsScreen({
  onSignOut,
  topInsetHandled,
}: {
  onSignOut?: () => void;
  topInsetHandled?: boolean;
}) {
  const theme = useAppTheme();
  const settings = useAppSettingsStore(state => state.settings);
  const setThemeMode = useAppSettingsStore(state => state.setThemeMode);
  const setGlassSettings = useAppSettingsStore(state => state.setGlassSettings);
  const [notifications, setNotifications] = useState(true);
  return (
    <ShowcasePage topInsetHandled={topInsetHandled}>
      <ShowcaseHeader
        title="Profile & settings"
        description="Account identity, appearance and material controls in mobile-native groups."
      />
      <GlassView style={styles.profile} variant="floating">
        <View style={[styles.avatar, { backgroundColor: theme.colors.accent }]}>
          <UserRound color={theme.colors.accentContrast} size={30} />
        </View>
        <View style={styles.flex}>
          <Text style={[theme.typography.title, { color: theme.colors.text }]}>
            Muhammad Chariev
          </Text>
          <Text
            style={[theme.typography.body, { color: theme.colors.textMuted }]}
          >
            demo@spacewhy.uz · Local profile
          </Text>
        </View>
      </GlassView>
      <GlassView style={styles.group} variant="surface">
        <SettingRow
          icon={<Moon color={theme.colors.accent} size={20} />}
          label="Dark appearance"
          description="Switches the shared theme store"
          trailing={
            <Switch
              accessibilityLabel="Dark appearance"
              onValueChange={value => setThemeMode(value ? 'dark' : 'light')}
              thumbColor={theme.colors.accentContrast}
              trackColor={{
                false: theme.colors.border,
                true: theme.colors.accent,
              }}
              value={settings.themeMode === 'dark'}
            />
          }
        />
        <SettingRow
          icon={<Bell color={theme.colors.accent} size={20} />}
          label="Demo notifications"
          description="Local example only"
          trailing={
            <Switch
              accessibilityLabel="Demo notifications"
              onValueChange={setNotifications}
              thumbColor={theme.colors.accentContrast}
              trackColor={{
                false: theme.colors.border,
                true: theme.colors.accent,
              }}
              value={notifications}
            />
          }
        />
      </GlassView>
      <GlassView style={styles.group} variant="surface">
        <Text
          accessibilityRole="header"
          style={[theme.typography.title, { color: theme.colors.text }]}
        >
          Liquid glass material
        </Text>
        {(
          [
            ['Optical intensity', 'opticalIntensity'],
            ['Transparency', 'transparency'],
            ['Surface liquidity', 'surfaceLiquidity'],
          ] as const
        ).map(([label, key]) => (
          <View key={key} style={styles.sliderBlock}>
            <View style={styles.rowBetween}>
              <Text
                style={[theme.typography.label, { color: theme.colors.text }]}
              >
                {label}
              </Text>
              <Text
                style={[
                  theme.typography.label,
                  { color: theme.colors.textMuted },
                ]}
              >
                {settings.glass[key]}%
              </Text>
            </View>
            <GlassSlider
              accessibilityLabel={label}
              maximumValue={100}
              minimumValue={0}
              onValueChange={value =>
                setGlassSettings({ [key]: Math.round(value) })
              }
              onSlidingComplete={value =>
                setGlassSettings({ [key]: Math.round(value) })
              }
              step={1}
              value={settings.glass[key]}
            />
          </View>
        ))}
      </GlassView>
      <Pressable
        accessibilityLabel="Sign out of local demo"
        accessibilityRole="button"
        accessibilityState={{ disabled: !onSignOut }}
        disabled={!onSignOut}
        onPress={onSignOut}
        style={[styles.signOut, !onSignOut && styles.disabled]}
      >
        <Text
          style={[theme.typography.label, { color: theme.colors.negative }]}
        >
          Sign out of local demo
        </Text>
      </Pressable>
    </ShowcasePage>
  );
}

function SettingRow({
  icon,
  label,
  description,
  trailing,
}: {
  icon: React.ReactNode;
  label: string;
  description: string;
  trailing: React.ReactNode;
}) {
  const theme = useAppTheme();
  return (
    <View style={styles.settingRow}>
      {icon}
      <View style={styles.flex}>
        <Text
          style={[
            theme.typography.title,
            styles.settingTitle,
            { color: theme.colors.text },
          ]}
        >
          {label}
        </Text>
        <Text
          style={[theme.typography.body, { color: theme.colors.textMuted }]}
        >
          {description}
        </Text>
      </View>
      {trailing}
    </View>
  );
}

const styles = StyleSheet.create({
  profile: { alignItems: 'center', flexDirection: 'row', gap: 14, padding: 18 },
  avatar: {
    alignItems: 'center',
    borderRadius: 30,
    height: 60,
    justifyContent: 'center',
    width: 60,
  },
  flex: { flex: 1 },
  group: { gap: 18, padding: 18 },
  settingRow: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: 12,
    minHeight: 52,
  },
  settingTitle: { fontSize: 16 },
  sliderBlock: { gap: 5 },
  rowBetween: { flexDirection: 'row', justifyContent: 'space-between' },
  signOut: { alignItems: 'center', justifyContent: 'center', minHeight: 48 },
  disabled: { opacity: 0.4 },
});
