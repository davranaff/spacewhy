import { useMemo } from 'react';
import { Platform, Pressable, StyleSheet, Text, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { useAppTheme } from '@/shared/theme';
import { DOCK_MIN_TARGET, DockSurface } from '@/widgets/dock';
import { DockIcon, type DockActionIconName } from '@/widgets/dock/dock-icon';

export type ContextualDockAction = Readonly<{
  id: string;
  label: string;
  accessibilityHint?: string;
  icon: DockActionIconName;
  disabled?: boolean;
  destructive?: boolean;
  onPress: () => void;
}>;

export type ContextualDockActions =
  | readonly []
  | readonly [ContextualDockAction]
  | readonly [ContextualDockAction, ContextualDockAction]
  | readonly [ContextualDockAction, ContextualDockAction, ContextualDockAction]
  | readonly [
      ContextualDockAction,
      ContextualDockAction,
      ContextualDockAction,
      ContextualDockAction,
    ];

type ContextualDockProps = {
  actions: ContextualDockActions;
  accessibilityLabel?: string;
};

export const ContextualDock = ({
  actions,
  accessibilityLabel = 'Contextual actions',
}: ContextualDockProps) => {
  const theme = useAppTheme();
  const insets = useSafeAreaInsets();
  const styles = useMemo(() => createStyles(theme), [theme]);

  return (
    <DockSurface
      accessibilityLabel={accessibilityLabel}
      bottomSafeArea={insets.bottom}
      mode="contextual"
    >
      <View style={styles.row}>
        {actions.map(action => (
          <Pressable
            accessibilityHint={action.accessibilityHint}
            accessibilityLabel={action.label}
            accessibilityRole="button"
            accessibilityState={{ disabled: action.disabled }}
            android_ripple={{
              color: theme.colors.border,
              borderless: true,
            }}
            disabled={action.disabled}
            key={action.id}
            onPress={action.onPress}
            style={({ pressed }) => [
              styles.action,
              action.disabled && styles.disabled,
              pressed && Platform.OS === 'ios' && styles.pressed,
            ]}
          >
            <DockIcon
              color={
                action.destructive ? theme.colors.negative : theme.colors.text
              }
              name={action.icon}
              size={20}
            />
            <Text
              maxFontSizeMultiplier={1.35}
              numberOfLines={1}
              style={[
                styles.label,
                action.destructive && styles.destructiveLabel,
              ]}
            >
              {action.label}
            </Text>
          </Pressable>
        ))}
      </View>
    </DockSurface>
  );
};

const createStyles = (theme: ReturnType<typeof useAppTheme>) =>
  StyleSheet.create({
    row: {
      alignItems: 'center',
      flex: 1,
      flexDirection: 'row',
      gap: 4,
      paddingHorizontal: 6,
      paddingVertical: 2,
    },
    action: {
      alignItems: 'center',
      borderRadius: 18,
      flex: 1,
      flexDirection: 'row',
      gap: 6,
      justifyContent: 'center',
      minHeight: DOCK_MIN_TARGET,
      minWidth: DOCK_MIN_TARGET,
      overflow: 'hidden',
      paddingHorizontal: 8,
    },
    pressed: {
      opacity: 0.72,
    },
    disabled: {
      opacity: 0.4,
    },
    label: {
      color: theme.colors.text,
      flexShrink: 1,
      fontSize: 12,
      fontWeight: '600',
    },
    destructiveLabel: {
      color: theme.colors.negative,
    },
  });
