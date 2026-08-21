import { useMemo } from 'react';
import {
  Image,
  Platform,
  Pressable,
  StyleSheet,
  Text,
  View,
  type ImageSourcePropType,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { useAppTheme } from '@/shared/theme';
import { DOCK_MIN_TARGET, DockSurface } from '@/widgets/dock';
import { DockIcon, type DockActionIconName } from '@/widgets/dock/dock-icon';

export type MiniPlayerStatus =
  | 'idle'
  | 'loading'
  | 'playing'
  | 'paused'
  | 'error';

export type MiniPlayerDockProps = {
  title: string;
  subtitle?: string;
  artwork?: ImageSourcePropType;
  progress: number;
  status: MiniPlayerStatus;
  expanded?: boolean;
  bottomSafeArea?: number;
  onTogglePlayback: () => void;
  onToggleExpanded: () => void;
  onClose: () => void;
  onRetry?: () => void;
  onPrevious?: () => void;
  onNext?: () => void;
};

const clampProgress = (progress: number): number =>
  Number.isFinite(progress) ? Math.min(1, Math.max(0, progress)) : 0;

export const MiniPlayerDock = ({
  title,
  subtitle,
  artwork,
  progress,
  status,
  expanded = false,
  bottomSafeArea,
  onTogglePlayback,
  onToggleExpanded,
  onClose,
  onRetry,
  onPrevious,
  onNext,
}: MiniPlayerDockProps) => {
  const theme = useAppTheme();
  const insets = useSafeAreaInsets();
  const styles = useMemo(() => createStyles(theme), [theme]);
  const safeProgress = clampProgress(progress);
  const hasError = status === 'error';
  const isPlaying = status === 'playing';
  const isLoading = status === 'loading';

  return (
    <DockSurface
      accessibilityLabel="Media player"
      bottomSafeArea={bottomSafeArea ?? insets.bottom}
      mode={expanded ? 'expanded-player' : 'mini-player'}
    >
      <View style={[styles.container, expanded && styles.containerExpanded]}>
        <View style={styles.primaryRow}>
          <Pressable
            accessibilityHint={
              expanded
                ? 'Collapses the player into the dock'
                : 'Opens the expanded player'
            }
            accessibilityLabel={`${title}${subtitle ? `, ${subtitle}` : ''}`}
            accessibilityRole="button"
            onPress={onToggleExpanded}
            style={({ pressed }) => [
              styles.track,
              pressed && Platform.OS === 'ios' && styles.pressed,
            ]}
          >
            {artwork ? (
              <Image
                accessibilityIgnoresInvertColors
                accessible={false}
                source={artwork}
                style={styles.artwork}
              />
            ) : (
              <View style={styles.artworkPlaceholder}>
                <DockIcon
                  color={theme.colors.textMuted}
                  name="music"
                  size={20}
                />
              </View>
            )}
            <View style={styles.copy}>
              <Text
                maxFontSizeMultiplier={1.5}
                numberOfLines={1}
                style={styles.title}
              >
                {title}
              </Text>
              <Text
                maxFontSizeMultiplier={1.5}
                numberOfLines={1}
                style={[styles.subtitle, hasError && styles.error]}
              >
                {hasError
                  ? 'Playback unavailable'
                  : subtitle ?? 'Spacewhy audio'}
              </Text>
            </View>
          </Pressable>

          {expanded ? (
            <PlayerAction
              accessibilityLabel="Collapse player"
              icon="collapse"
              onPress={onToggleExpanded}
            />
          ) : (
            <PlaybackAction
              hasError={hasError}
              isLoading={isLoading}
              isPlaying={isPlaying}
              onRetry={onRetry}
              onTogglePlayback={onTogglePlayback}
            />
          )}
          <PlayerAction
            accessibilityLabel="Close player"
            icon="close"
            onPress={onClose}
          />
        </View>

        {expanded ? (
          <View style={styles.transportRow}>
            <PlayerAction
              accessibilityLabel="Previous track"
              icon="skip-back"
              onPress={onPrevious}
            />
            <PlaybackAction
              hasError={hasError}
              isLoading={isLoading}
              isPlaying={isPlaying}
              onRetry={onRetry}
              onTogglePlayback={onTogglePlayback}
            />
            <PlayerAction
              accessibilityLabel="Next track"
              icon="skip-forward"
              onPress={onNext}
            />
          </View>
        ) : null}

        <View
          accessibilityLabel={`${Math.round(
            safeProgress * 100,
          )} percent played`}
          accessibilityRole="progressbar"
          accessibilityValue={{ min: 0, max: 100, now: safeProgress * 100 }}
          style={styles.progressTrack}
        >
          <View
            style={[styles.progressFill, { width: `${safeProgress * 100}%` }]}
          />
        </View>
      </View>
    </DockSurface>
  );
};

type PlayerActionProps = {
  accessibilityLabel: string;
  disabled?: boolean;
  icon: Extract<
    DockActionIconName,
    | 'close'
    | 'collapse'
    | 'pause'
    | 'play'
    | 'refresh'
    | 'skip-back'
    | 'skip-forward'
  >;
  onPress?: () => void;
};

type PlaybackActionProps = {
  hasError: boolean;
  isLoading: boolean;
  isPlaying: boolean;
  onRetry?: () => void;
  onTogglePlayback: () => void;
};

const PlaybackAction = ({
  hasError,
  isLoading,
  isPlaying,
  onRetry,
  onTogglePlayback,
}: PlaybackActionProps) => (
  <PlayerAction
    accessibilityLabel={
      hasError ? 'Retry playback' : isPlaying ? 'Pause' : 'Play'
    }
    disabled={isLoading}
    icon={hasError ? 'refresh' : isPlaying ? 'pause' : 'play'}
    onPress={hasError ? onRetry : onTogglePlayback}
  />
);

const PlayerAction = ({
  accessibilityLabel,
  disabled,
  icon,
  onPress,
}: PlayerActionProps) => {
  const theme = useAppTheme();
  const isDisabled = disabled || !onPress;
  const styles = useMemo(() => createStyles(theme), [theme]);

  return (
    <Pressable
      accessibilityLabel={accessibilityLabel}
      accessibilityRole="button"
      accessibilityState={{ disabled: isDisabled }}
      android_ripple={{ color: theme.colors.border, borderless: true }}
      disabled={isDisabled}
      onPress={onPress}
      style={({ pressed }) => [
        styles.action,
        isDisabled && styles.disabled,
        pressed && Platform.OS === 'ios' && styles.pressed,
      ]}
    >
      <DockIcon color={theme.colors.text} name={icon} size={22} />
    </Pressable>
  );
};

const createStyles = (theme: ReturnType<typeof useAppTheme>) =>
  StyleSheet.create({
    container: {
      flex: 1,
      paddingHorizontal: 8,
      paddingVertical: 6,
    },
    containerExpanded: {
      paddingVertical: 4,
    },
    primaryRow: {
      alignItems: 'center',
      flexDirection: 'row',
      gap: 4,
    },
    track: {
      alignItems: 'center',
      borderRadius: 18,
      flex: 1,
      flexDirection: 'row',
      gap: 10,
      minHeight: DOCK_MIN_TARGET,
      minWidth: 0,
      paddingHorizontal: 4,
    },
    artwork: {
      backgroundColor: theme.colors.surfaceElevated,
      borderRadius: 12,
      height: 44,
      width: 44,
    },
    artworkPlaceholder: {
      alignItems: 'center',
      backgroundColor: theme.colors.surface,
      borderRadius: 12,
      height: 44,
      justifyContent: 'center',
      width: 44,
    },
    copy: {
      flex: 1,
      minWidth: 0,
    },
    title: {
      color: theme.colors.text,
      fontSize: 14,
      fontWeight: '700',
      lineHeight: 18,
    },
    subtitle: {
      color: theme.colors.textMuted,
      fontSize: 12,
      lineHeight: 16,
    },
    error: {
      color: theme.colors.negative,
    },
    action: {
      alignItems: 'center',
      borderRadius: DOCK_MIN_TARGET / 2,
      height: DOCK_MIN_TARGET,
      justifyContent: 'center',
      overflow: 'hidden',
      width: DOCK_MIN_TARGET,
    },
    pressed: {
      opacity: 0.72,
    },
    disabled: {
      opacity: 0.4,
    },
    progressTrack: {
      backgroundColor: theme.colors.border,
      bottom: 2,
      height: 2,
      left: 18,
      overflow: 'hidden',
      position: 'absolute',
      right: 18,
    },
    progressFill: {
      backgroundColor: theme.colors.accent,
      height: '100%',
    },
    transportRow: {
      alignItems: 'center',
      flex: 1,
      flexDirection: 'row',
      justifyContent: 'center',
    },
  });
