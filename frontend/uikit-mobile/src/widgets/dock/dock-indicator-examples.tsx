import { useMemo } from 'react';
import { StyleSheet, View } from 'react-native';

import { useAppTheme } from '@/shared/theme';
import { GlassView } from '@/shared/ui';

export type DockIndicatorVariant =
  | 'dot'
  | 'glass-pill'
  | 'segmented'
  | 'progress';

type DockIndicatorExamplesProps = {
  activeIndex: number;
  count: number;
  variant: DockIndicatorVariant;
};

const clampIndex = (index: number, count: number): number =>
  Math.min(Math.max(0, index), Math.max(0, count - 1));

export const DockIndicatorExamples = ({
  activeIndex,
  count,
  variant,
}: DockIndicatorExamplesProps) => {
  const theme = useAppTheme();
  const styles = useMemo(() => createStyles(theme), [theme]);
  const safeCount = Math.max(1, Math.floor(count));
  const safeIndex = clampIndex(activeIndex, safeCount);

  if (variant === 'progress') {
    return (
      <View
        accessibilityLabel={`Page ${safeIndex + 1} of ${safeCount}`}
        accessibilityRole="progressbar"
        accessibilityValue={{ min: 1, max: safeCount, now: safeIndex + 1 }}
        style={styles.progressTrack}
      >
        <View
          style={[
            styles.progressFill,
            { width: `${((safeIndex + 1) / safeCount) * 100}%` },
          ]}
        />
      </View>
    );
  }

  return (
    <View
      accessibilityLabel={`Page ${safeIndex + 1} of ${safeCount}`}
      style={[styles.row, variant === 'segmented' && styles.segmentedTrack]}
    >
      {Array.from({ length: safeCount }, (_, index) => {
        const active = index === safeIndex;

        if (variant === 'glass-pill' && active) {
          return (
            <GlassView key={index} variant="control" style={styles.pill} />
          );
        }

        return (
          <View
            key={index}
            style={[
              variant === 'segmented' ? styles.segment : styles.dot,
              active && styles.active,
            ]}
          />
        );
      })}
    </View>
  );
};

const createStyles = (theme: ReturnType<typeof useAppTheme>) =>
  StyleSheet.create({
    row: {
      alignItems: 'center',
      flexDirection: 'row',
      gap: 6,
    },
    dot: {
      backgroundColor: theme.colors.textMuted,
      borderRadius: 3,
      height: 6,
      width: 6,
    },
    pill: {
      height: 6,
      width: 24,
    },
    active: {
      backgroundColor: theme.colors.accent,
    },
    segmentedTrack: {
      gap: 2,
    },
    segment: {
      backgroundColor: theme.colors.border,
      borderRadius: 2,
      height: 4,
      width: 18,
    },
    progressTrack: {
      backgroundColor: theme.colors.border,
      borderRadius: 2,
      height: 4,
      overflow: 'hidden',
      width: 96,
    },
    progressFill: {
      backgroundColor: theme.colors.accent,
      borderRadius: 2,
      height: '100%',
    },
  });
