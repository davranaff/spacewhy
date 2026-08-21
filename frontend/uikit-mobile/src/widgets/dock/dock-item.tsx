import { Platform, Pressable, StyleSheet, Text, View } from 'react-native';

import type { DockDestination } from '@/app/navigation/navigation-contracts';
import { useAppSettingsStore } from '@/shared/settings';
import { useAppTheme } from '@/shared/theme';
import { DockIcon } from '@/widgets/dock/dock-icon';
import { DOCK_MIN_TARGET } from '@/widgets/dock/dock-layout';

type DockItemProps = {
  destination: DockDestination;
  selected: boolean;
  compact: boolean;
  onPress: () => void;
  onLongPress: () => void;
};

export const DockItem = ({
  destination,
  selected,
  compact,
  onPress,
  onLongPress,
}: DockItemProps) => {
  const theme = useAppTheme();
  const dockTone = useAppSettingsStore(state => state.settings.dock.tone);
  const dockIsDark =
    dockTone === 'dark' || (dockTone === 'adaptive' && theme.isDark);
  const selectedColor = dockIsDark ? '#FFFFFF' : '#111216';
  const idleColor = dockIsDark
    ? 'rgba(255,255,255,0.58)'
    : 'rgba(17,18,22,0.58)';

  return (
    <Pressable
      accessibilityHint={destination.accessibilityHint}
      accessibilityLabel={destination.label}
      accessibilityRole="tab"
      accessibilityState={{ selected }}
      android_ripple={{ color: 'rgba(255,255,255,0.10)', borderless: true }}
      hitSlop={4}
      onLongPress={onLongPress}
      onPress={onPress}
      style={({ pressed }) => [
        styles.pressable,
        compact && styles.pressableCompact,
        pressed && Platform.OS === 'ios' && styles.pressed,
      ]}
    >
      <View style={styles.content}>
        <DockIcon
          name={destination.icon}
          size={20}
          color={selected ? selectedColor : idleColor}
        />
        {!compact ? (
          <Text
            maxFontSizeMultiplier={1.35}
            numberOfLines={1}
            style={[
              styles.label,
              { color: selected ? selectedColor : idleColor },
              selected && styles.labelSelected,
            ]}
          >
            {destination.label}
          </Text>
        ) : null}
      </View>
    </Pressable>
  );
};

const styles = StyleSheet.create({
  pressable: {
    alignItems: 'center',
    borderRadius: 22,
    flex: 1,
    justifyContent: 'center',
    minHeight: DOCK_MIN_TARGET,
    minWidth: DOCK_MIN_TARGET,
    overflow: 'hidden',
    paddingHorizontal: 4,
  },
  pressableCompact: {
    maxWidth: 64,
  },
  pressed: {
    opacity: 0.72,
  },
  content: {
    alignItems: 'center',
    gap: 2,
    justifyContent: 'center',
    zIndex: 2,
  },
  label: {
    fontSize: 10,
    fontWeight: '500',
    lineHeight: 12,
  },
  labelSelected: {
    fontWeight: '700',
  },
});
