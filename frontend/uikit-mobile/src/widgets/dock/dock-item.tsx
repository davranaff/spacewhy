import { useEffect, useMemo, useRef } from 'react';
import {
  Animated,
  Easing,
  Platform,
  Pressable,
  StyleSheet,
  Text,
  View,
} from 'react-native';

import type { DockDestination } from '@/app/navigation/navigation-contracts';
import { useAppTheme } from '@/shared/theme';
import { GlassView } from '@/shared/ui';
import { DockIcon } from '@/widgets/dock/dock-icon';
import { DOCK_MIN_TARGET } from '@/widgets/dock/dock-layout';
import { useReducedMotion } from '@/widgets/dock/use-reduced-motion';

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
  const reduceMotion = useReducedMotion();
  const activeOpacity = useRef(new Animated.Value(selected ? 1 : 0)).current;
  const activeScale = useRef(new Animated.Value(selected ? 1 : 0.92)).current;
  const styles = useMemo(() => createStyles(theme), [theme]);

  useEffect(() => {
    const duration = reduceMotion ? 0 : 160;
    activeOpacity.stopAnimation();
    activeScale.stopAnimation();

    Animated.parallel([
      Animated.timing(activeOpacity, {
        toValue: selected ? 1 : 0,
        duration,
        easing: Easing.out(Easing.cubic),
        useNativeDriver: true,
      }),
      Animated.timing(activeScale, {
        toValue: selected ? 1 : 0.92,
        duration,
        easing: Easing.out(Easing.cubic),
        useNativeDriver: true,
      }),
    ]).start();

    return () => {
      activeOpacity.stopAnimation();
      activeScale.stopAnimation();
    };
  }, [activeOpacity, activeScale, reduceMotion, selected]);

  return (
    <Pressable
      accessibilityHint={destination.accessibilityHint}
      accessibilityLabel={destination.label}
      accessibilityRole="tab"
      accessibilityState={{ selected }}
      android_ripple={{ color: theme.colors.border, borderless: true }}
      hitSlop={4}
      onLongPress={onLongPress}
      onPress={onPress}
      style={({ pressed }) => [
        styles.pressable,
        compact && styles.pressableCompact,
        pressed && Platform.OS === 'ios' && styles.pressed,
      ]}
    >
      <Animated.View
        pointerEvents="none"
        style={[
          styles.indicator,
          { opacity: activeOpacity, transform: [{ scale: activeScale }] },
        ]}
      >
        <GlassView variant="control" style={StyleSheet.absoluteFill} />
      </Animated.View>

      <View style={styles.content}>
        <DockIcon
          name={destination.icon}
          size={20}
          color={selected ? theme.colors.text : theme.colors.textMuted}
        />
        {!compact ? (
          <Text
            maxFontSizeMultiplier={1.35}
            numberOfLines={1}
            style={[
              styles.label,
              selected ? styles.labelSelected : styles.labelIdle,
            ]}
          >
            {destination.label}
          </Text>
        ) : null}
      </View>
    </Pressable>
  );
};

const createStyles = (theme: ReturnType<typeof useAppTheme>) =>
  StyleSheet.create({
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
    indicator: {
      bottom: 2,
      left: 2,
      position: 'absolute',
      right: 2,
      top: 2,
    },
    content: {
      alignItems: 'center',
      gap: 2,
      justifyContent: 'center',
      zIndex: 1,
    },
    label: {
      fontSize: 10,
      lineHeight: 12,
    },
    labelSelected: {
      color: theme.colors.text,
      fontWeight: '700',
    },
    labelIdle: {
      color: theme.colors.textMuted,
      fontWeight: '500',
    },
  });
