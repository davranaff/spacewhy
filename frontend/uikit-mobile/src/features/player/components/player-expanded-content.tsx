import { useEffect, useState } from 'react';
import {
  ActivityIndicator,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import Slider from '@react-native-community/slider';
import {
  ChevronDown,
  Clock3,
  CircleAlert,
  ListMusic,
  Music2,
  Pause,
  Play,
  RotateCw,
  SkipBack,
  SkipForward,
  Volume2,
  X,
} from 'lucide-react-native';

import { useAppTheme } from '@/shared/theme';
import { GlassView } from '@/shared/ui/glass-view';
import { PLAYER_DEMO_QUEUE } from '@/features/player/data/demo-queue';
import { formatPlayerTime } from '@/features/player/lib/format-time';
import { usePlayerReducedMotion } from '@/features/player/hooks/use-player-reduced-motion';
import { playerController } from '@/features/player/lib/player-controller';
import { runPlayerCommand } from '@/features/player/lib/run-player-command';
import {
  selectCurrentTrack,
  usePlayerStore,
} from '@/features/player/store/player-store';

type Props = Readonly<{
  onCollapse?: () => void;
  onClose?: () => void;
}>;

export function PlayerExpandedContent({ onCollapse, onClose }: Props) {
  const theme = useAppTheme();
  const track = usePlayerStore(selectCurrentTrack);
  const queue = usePlayerStore(state => state.queue);
  const currentIndex = usePlayerStore(state => state.currentIndex);
  const status = usePlayerStore(state => state.status);
  const position = usePlayerStore(state => state.position);
  const duration = usePlayerStore(state => state.duration);
  const error = usePlayerStore(state => state.error);
  const [seekValue, setSeekValue] = useState(position);
  const [isSeeking, setIsSeeking] = useState(false);
  const reducedMotion = usePlayerReducedMotion();

  useEffect(() => {
    if (!isSeeking) {
      setSeekValue(position);
    }
  }, [isSeeking, position]);

  const isLoading = status === 'loading';
  const isPlaying = status === 'playing';
  const hasError = status === 'error' || status === 'unavailable';
  const canSeek = duration > 0 && !isLoading && !hasError;

  if (!track) {
    return (
      <View style={styles.centerState}>
        <View
          style={[
            styles.emptyIcon,
            { backgroundColor: theme.colors.surfaceElevated },
          ]}
        >
          <ListMusic color={theme.colors.accent} size={34} />
        </View>
        <Text
          accessibilityRole="header"
          style={[theme.typography.title, { color: theme.colors.text }]}
        >
          Your queue is empty
        </Text>
        <Text
          style={[
            theme.typography.body,
            styles.centerCopy,
            { color: theme.colors.textMuted },
          ]}
        >
          Load the royalty-free demo queue to test native audio playback.
        </Text>
        <PlayerTextButton
          label="Load demo queue"
          onPress={() =>
            runPlayerCommand(playerController.setQueue(PLAYER_DEMO_QUEUE))
          }
        />
      </View>
    );
  }

  return (
    <ScrollView
      contentContainerStyle={styles.content}
      showsVerticalScrollIndicator={false}
    >
      <View style={styles.header}>
        <PlayerIconButton
          Icon={ChevronDown}
          accessibilityLabel="Collapse player"
          disabled={!onCollapse}
          onPress={onCollapse}
        />
        <View style={styles.headerCopy}>
          <Text style={[styles.overline, { color: theme.colors.textMuted }]}>
            NOW PLAYING
          </Text>
          <Text
            numberOfLines={1}
            style={[theme.typography.label, { color: theme.colors.text }]}
          >
            {currentIndex + 1} of {queue.length}
          </Text>
        </View>
        <PlayerIconButton
          Icon={X}
          accessibilityLabel="Close player"
          onPress={() => {
            runPlayerCommand(playerController.close());
            onClose?.();
          }}
        />
      </View>

      <View
        style={[
          styles.artwork,
          {
            backgroundColor: theme.colors.surface,
            borderColor: theme.colors.border,
          },
        ]}
      >
        <View
          style={[
            styles.artworkOrb,
            styles.artworkOrbOne,
            { backgroundColor: theme.colors.accent },
          ]}
        />
        <View
          style={[
            styles.artworkOrb,
            styles.artworkOrbTwo,
            { backgroundColor: theme.colors.positive },
          ]}
        />
        <GlassView variant="floating" style={styles.artworkGlass}>
          <Music2 color={theme.colors.text} size={54} strokeWidth={1.4} />
        </GlassView>
      </View>

      <View style={styles.trackCopy}>
        <Text
          accessibilityRole="header"
          numberOfLines={2}
          style={[
            theme.typography.display,
            styles.trackTitle,
            { color: theme.colors.text },
          ]}
        >
          {track.title}
        </Text>
        <Text
          numberOfLines={1}
          style={[theme.typography.body, { color: theme.colors.textMuted }]}
        >
          {track.artist}
        </Text>
      </View>

      {hasError ? (
        <View
          accessibilityRole="alert"
          style={[
            styles.error,
            {
              backgroundColor: `${theme.colors.negative}16`,
              borderColor: `${theme.colors.negative}55`,
            },
          ]}
        >
          <CircleAlert color={theme.colors.negative} size={21} />
          <View style={styles.flex}>
            <Text
              style={[theme.typography.label, { color: theme.colors.negative }]}
            >
              {status === 'unavailable'
                ? 'Native player unavailable'
                : 'Playback failed'}
            </Text>
            <Text style={[styles.errorCopy, { color: theme.colors.text }]}>
              {error?.message ?? 'Check your connection and try again.'}
            </Text>
          </View>
          <PlayerIconButton
            Icon={RotateCw}
            accessibilityLabel="Retry playback"
            onPress={() => runPlayerCommand(playerController.retry())}
          />
        </View>
      ) : null}

      <View style={styles.seekGroup}>
        <Slider
          accessibilityLabel="Playback position"
          accessibilityValue={{
            min: 0,
            max: Math.round(duration),
            now: Math.round(seekValue),
            text: `${formatPlayerTime(seekValue)} of ${formatPlayerTime(
              duration,
            )}`,
          }}
          disabled={!canSeek}
          maximumTrackTintColor={theme.colors.border}
          maximumValue={Math.max(duration, 1)}
          minimumTrackTintColor={theme.colors.accent}
          minimumValue={0}
          onSlidingComplete={value => {
            setIsSeeking(false);
            runPlayerCommand(playerController.seek(value));
          }}
          onSlidingStart={() => setIsSeeking(true)}
          onValueChange={setSeekValue}
          step={0.1}
          thumbTintColor={theme.colors.text}
          value={seekValue}
        />
        <View style={styles.timeRow}>
          <Text style={[styles.time, { color: theme.colors.textMuted }]}>
            {formatPlayerTime(seekValue)}
          </Text>
          <Text style={[styles.time, { color: theme.colors.textMuted }]}>
            {isLoading ? 'Loading…' : formatPlayerTime(duration)}
          </Text>
        </View>
      </View>

      <View style={styles.transport}>
        <PlayerIconButton
          large
          Icon={SkipBack}
          accessibilityLabel="Previous track"
          onPress={() => runPlayerCommand(playerController.previous())}
        />
        <Pressable
          accessibilityLabel={
            hasError ? 'Retry playback' : isPlaying ? 'Pause' : 'Play'
          }
          accessibilityRole="button"
          accessibilityState={{ disabled: isLoading }}
          disabled={isLoading}
          onPress={
            hasError
              ? () => runPlayerCommand(playerController.retry())
              : () => runPlayerCommand(playerController.togglePlayback())
          }
          style={[styles.playButton, { backgroundColor: theme.colors.text }]}
        >
          {isLoading && !reducedMotion ? (
            <ActivityIndicator color={theme.colors.canvas} size="large" />
          ) : isLoading ? (
            <Clock3 color={theme.colors.canvas} size={30} />
          ) : hasError ? (
            <RotateCw color={theme.colors.canvas} size={29} />
          ) : isPlaying ? (
            <Pause
              color={theme.colors.canvas}
              fill={theme.colors.canvas}
              size={30}
            />
          ) : (
            <Play
              color={theme.colors.canvas}
              fill={theme.colors.canvas}
              size={30}
            />
          )}
        </Pressable>
        <PlayerIconButton
          large
          Icon={SkipForward}
          accessibilityLabel="Next track"
          onPress={() => runPlayerCommand(playerController.next())}
        />
      </View>

      <View style={styles.volumeRow}>
        <Volume2 color={theme.colors.textMuted} size={18} />
        <Text style={[styles.systemVolume, { color: theme.colors.textMuted }]}>
          Volume follows the system controls
        </Text>
      </View>

      <View style={styles.queueSection}>
        <View style={styles.queueHeading}>
          <Text
            accessibilityRole="header"
            style={[theme.typography.title, { color: theme.colors.text }]}
          >
            Up next
          </Text>
          <Text
            style={[theme.typography.label, { color: theme.colors.textMuted }]}
          >
            {queue.length} tracks
          </Text>
        </View>
        <GlassView variant="surface" style={styles.queueSurface}>
          {queue.map((item, index) => {
            const selected = index === currentIndex;
            return (
              <Pressable
                key={item.id}
                accessibilityLabel={`${item.title}, ${item.artist}`}
                accessibilityRole="button"
                accessibilityState={{ selected }}
                onPress={() =>
                  runPlayerCommand(playerController.selectTrack(index))
                }
                style={[
                  styles.queueRow,
                  selected && { backgroundColor: theme.colors.surfaceElevated },
                ]}
              >
                <View
                  style={[
                    styles.queueArtwork,
                    {
                      backgroundColor: selected
                        ? theme.colors.accent
                        : theme.colors.surfaceElevated,
                    },
                  ]}
                >
                  {selected && isPlaying ? (
                    <Volume2 color={theme.colors.accentContrast} size={18} />
                  ) : (
                    <Music2
                      color={
                        selected
                          ? theme.colors.accentContrast
                          : theme.colors.textMuted
                      }
                      size={18}
                    />
                  )}
                </View>
                <View style={styles.flex}>
                  <Text
                    numberOfLines={1}
                    style={[
                      theme.typography.label,
                      { color: theme.colors.text },
                    ]}
                  >
                    {item.title}
                  </Text>
                  <Text
                    numberOfLines={1}
                    style={[
                      styles.queueArtist,
                      { color: theme.colors.textMuted },
                    ]}
                  >
                    {item.artist}
                  </Text>
                </View>
                <Text
                  style={[
                    styles.queueIndex,
                    {
                      color: selected
                        ? theme.colors.accent
                        : theme.colors.textMuted,
                    },
                  ]}
                >
                  {String(index + 1).padStart(2, '0')}
                </Text>
              </Pressable>
            );
          })}
        </GlassView>
      </View>
    </ScrollView>
  );
}

type IconButtonProps = Readonly<{
  Icon: typeof Play;
  accessibilityLabel: string;
  disabled?: boolean;
  large?: boolean;
  onPress?: () => void;
}>;

function PlayerIconButton({
  Icon,
  accessibilityLabel,
  disabled,
  large,
  onPress,
}: IconButtonProps) {
  const theme = useAppTheme();
  const isDisabled = disabled || !onPress;
  return (
    <Pressable
      accessibilityLabel={accessibilityLabel}
      accessibilityRole="button"
      accessibilityState={{ disabled: isDisabled }}
      disabled={isDisabled}
      onPress={onPress}
      style={[
        styles.iconButton,
        large && styles.iconButtonLarge,
        {
          backgroundColor: theme.colors.surface,
          borderColor: theme.colors.border,
        },
        isDisabled && styles.disabled,
      ]}
    >
      <Icon color={theme.colors.text} size={large ? 27 : 20} />
    </Pressable>
  );
}

function PlayerTextButton({
  label,
  onPress,
}: {
  label: string;
  onPress: () => void;
}) {
  const theme = useAppTheme();
  return (
    <Pressable
      accessibilityLabel={label}
      accessibilityRole="button"
      onPress={onPress}
      style={[styles.textButton, { backgroundColor: theme.colors.accent }]}
    >
      <Text
        style={[theme.typography.label, { color: theme.colors.accentContrast }]}
      >
        {label}
      </Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  content: { paddingHorizontal: 20, paddingBottom: 60, gap: 20 },
  header: {
    minHeight: 52,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  headerCopy: { alignItems: 'center', gap: 2 },
  overline: {
    fontSize: 10,
    lineHeight: 14,
    fontWeight: '800',
    letterSpacing: 1.2,
  },
  artwork: {
    aspectRatio: 1,
    maxHeight: 410,
    borderRadius: 40,
    borderWidth: StyleSheet.hairlineWidth,
    overflow: 'hidden',
    alignItems: 'center',
    justifyContent: 'center',
  },
  artworkOrb: {
    position: 'absolute',
    width: '62%',
    aspectRatio: 1,
    borderRadius: 999,
    opacity: 0.55,
  },
  artworkOrbOne: { right: '-16%', top: '-10%' },
  artworkOrbTwo: { left: '-20%', bottom: '-14%', opacity: 0.26 },
  artworkGlass: {
    width: '52%',
    aspectRatio: 1,
    borderRadius: 999,
    alignItems: 'center',
    justifyContent: 'center',
  },
  trackCopy: { alignItems: 'center', gap: 5, paddingHorizontal: 12 },
  trackTitle: { fontSize: 28, lineHeight: 34, textAlign: 'center' },
  error: {
    borderRadius: 20,
    borderWidth: StyleSheet.hairlineWidth,
    padding: 14,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
  },
  errorCopy: { fontSize: 12, lineHeight: 17, marginTop: 2 },
  seekGroup: { gap: 2 },
  timeRow: { flexDirection: 'row', justifyContent: 'space-between' },
  time: { fontSize: 11, lineHeight: 15, fontVariant: ['tabular-nums'] },
  transport: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 22,
  },
  playButton: {
    width: 68,
    height: 68,
    borderRadius: 34,
    alignItems: 'center',
    justifyContent: 'center',
  },
  iconButton: {
    width: 48,
    height: 48,
    borderRadius: 24,
    borderWidth: StyleSheet.hairlineWidth,
    alignItems: 'center',
    justifyContent: 'center',
  },
  iconButtonLarge: { width: 52, height: 52, borderRadius: 26 },
  disabled: { opacity: 0.4 },
  volumeRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    paddingHorizontal: 8,
  },
  systemVolume: { fontSize: 12, lineHeight: 17 },
  queueSection: { gap: 12, marginTop: 6 },
  queueHeading: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  queueSurface: { borderRadius: 26, overflow: 'hidden' },
  queueRow: {
    minHeight: 68,
    paddingHorizontal: 12,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 11,
  },
  queueArtwork: {
    width: 44,
    height: 44,
    borderRadius: 14,
    alignItems: 'center',
    justifyContent: 'center',
  },
  queueArtist: { fontSize: 12, lineHeight: 16, marginTop: 2 },
  queueIndex: { fontSize: 11, lineHeight: 15, fontVariant: ['tabular-nums'] },
  centerState: {
    flex: 1,
    minHeight: 560,
    paddingHorizontal: 28,
    alignItems: 'center',
    justifyContent: 'center',
    gap: 12,
  },
  emptyIcon: {
    width: 76,
    height: 76,
    borderRadius: 26,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 4,
  },
  centerCopy: { textAlign: 'center', maxWidth: 320 },
  textButton: {
    minHeight: 48,
    borderRadius: 16,
    paddingHorizontal: 20,
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: 4,
  },
});
