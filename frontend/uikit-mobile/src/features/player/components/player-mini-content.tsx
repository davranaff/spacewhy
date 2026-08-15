import {
  ActivityIndicator,
  Pressable,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { Clock3, Music2, Pause, Play, RotateCw } from 'lucide-react-native';

import { useAppTheme } from '@/shared/theme';
import { GlassView } from '@/shared/ui/glass-view';
import { usePlayerDockModel } from '@/features/player/hooks/use-player-dock-model';
import { usePlayerReducedMotion } from '@/features/player/hooks/use-player-reduced-motion';

type Props = Readonly<{
  onExpand?: () => void;
}>;

export function PlayerMiniContent({ onExpand }: Props) {
  const theme = useAppTheme();
  const player = usePlayerDockModel();
  const reducedMotion = usePlayerReducedMotion();
  const isLoading = player.status === 'loading';
  const isError = player.status === 'error';
  const isPlaying = player.status === 'playing';

  if (!player.hasTrack) {
    return null;
  }

  return (
    <GlassView
      accessibilityLabel="Audio player"
      variant="floating"
      style={styles.container}
    >
      <Pressable
        accessibilityHint="Opens the full player"
        accessibilityLabel={`${player.title}, ${player.subtitle ?? 'audio'}`}
        accessibilityRole="button"
        disabled={!onExpand}
        onPress={onExpand}
        style={styles.track}
      >
        <View
          style={[
            styles.artwork,
            { backgroundColor: theme.colors.surfaceElevated },
          ]}
        >
          <Music2 color={theme.colors.accent} size={20} />
        </View>
        <View style={styles.copy}>
          <Text
            numberOfLines={1}
            style={[
              theme.typography.label,
              styles.title,
              { color: theme.colors.text },
            ]}
          >
            {player.title}
          </Text>
          <Text
            numberOfLines={1}
            style={[styles.subtitle, { color: theme.colors.textMuted }]}
          >
            {isError ? 'Playback unavailable' : player.subtitle}
          </Text>
        </View>
      </Pressable>

      <Pressable
        accessibilityLabel={
          isError ? 'Retry playback' : isPlaying ? 'Pause' : 'Play'
        }
        accessibilityRole="button"
        accessibilityState={{ disabled: isLoading }}
        disabled={isLoading}
        onPress={isError ? player.onRetry : player.onTogglePlayback}
        style={[styles.action, { backgroundColor: theme.colors.text }]}
      >
        {isLoading && !reducedMotion ? (
          <ActivityIndicator color={theme.colors.canvas} size="small" />
        ) : isLoading ? (
          <Clock3 color={theme.colors.canvas} size={19} />
        ) : isError ? (
          <RotateCw color={theme.colors.canvas} size={19} />
        ) : isPlaying ? (
          <Pause
            color={theme.colors.canvas}
            fill={theme.colors.canvas}
            size={19}
          />
        ) : (
          <Play
            color={theme.colors.canvas}
            fill={theme.colors.canvas}
            size={19}
          />
        )}
      </Pressable>

      <View
        style={[styles.progressTrack, { backgroundColor: theme.colors.border }]}
      >
        <View
          style={[
            styles.progress,
            {
              backgroundColor: theme.colors.accent,
              width: `${player.progress * 100}%`,
            },
          ]}
        />
      </View>
    </GlassView>
  );
}

const styles = StyleSheet.create({
  container: {
    minHeight: 72,
    borderRadius: 24,
    padding: 10,
    paddingBottom: 13,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
  },
  track: {
    flex: 1,
    minHeight: 48,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
  },
  artwork: {
    width: 44,
    height: 44,
    borderRadius: 14,
    alignItems: 'center',
    justifyContent: 'center',
  },
  copy: { flex: 1, gap: 2 },
  title: { fontSize: 14, lineHeight: 18 },
  subtitle: { fontSize: 12, lineHeight: 16 },
  action: {
    width: 48,
    height: 48,
    borderRadius: 24,
    alignItems: 'center',
    justifyContent: 'center',
  },
  progressTrack: {
    position: 'absolute',
    left: 18,
    right: 18,
    bottom: 6,
    height: 2,
    borderRadius: 1,
    overflow: 'hidden',
  },
  progress: { height: '100%', borderRadius: 1 },
});
