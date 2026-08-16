import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  Animated,
  Easing,
  StyleSheet,
  View,
  type LayoutChangeEvent,
} from 'react-native';
import { Gesture, GestureDetector } from 'react-native-gesture-handler';

import { useAppTheme } from '@/shared/theme';

import { GlassView } from './glass-view';

const THUMB_TOUCH_WIDTH = 72;
const THUMB_TOUCH_HEIGHT = 52;
const THUMB_VISUAL_WIDTH = 68;
const THUMB_VISUAL_HEIGHT = 46;
const TRACK_HEIGHT = 6;

export type GlassSliderProps = {
  accessibilityLabel: string;
  value: number;
  minimumValue?: number;
  maximumValue?: number;
  step?: number;
  disabled?: boolean;
  accessibilityText?: string;
  onValueChange?: (value: number) => void;
  onSlidingStart?: () => void;
  onSlidingComplete?: (value: number) => void;
};

function clamp(value: number, minimum: number, maximum: number): number {
  return Math.min(maximum, Math.max(minimum, value));
}

export function GlassSlider({
  accessibilityLabel,
  value,
  minimumValue = 0,
  maximumValue = 100,
  step = 1,
  disabled = false,
  accessibilityText,
  onValueChange,
  onSlidingStart,
  onSlidingComplete,
}: GlassSliderProps) {
  const theme = useAppTheme();
  const [width, setWidth] = useState(0);
  const [dragging, setDragging] = useState(false);
  const thumbScale = useRef(new Animated.Value(1)).current;
  const range = Math.max(1, maximumValue - minimumValue);
  const normalizedValue = clamp(value, minimumValue, maximumValue);
  const progress = (normalizedValue - minimumValue) / range;
  const travel = Math.max(0, width - THUMB_TOUCH_WIDTH);
  const thumbX = progress * travel;

  useEffect(() => {
    Animated.timing(thumbScale, {
      toValue: dragging ? 1.04 : 1,
      duration: theme.motion.quick,
      easing: Easing.out(Easing.cubic),
      useNativeDriver: true,
    }).start();
  }, [dragging, theme.motion.quick, thumbScale]);

  const valueForX = useCallback(
    (x: number): number => {
      const usableWidth = Math.max(1, width - THUMB_TOUCH_WIDTH);
      const rawProgress = clamp(
        (x - THUMB_TOUCH_WIDTH / 2) / usableWidth,
        0,
        1,
      );
      const rawValue = minimumValue + rawProgress * range;
      const steppedValue = Math.round(rawValue / step) * step;
      return clamp(steppedValue, minimumValue, maximumValue);
    },
    [maximumValue, minimumValue, range, step, width],
  );

  const updateFromX = useCallback(
    (x: number) => {
      if (disabled) return;
      onValueChange?.(valueForX(x));
    },
    [disabled, onValueChange, valueForX],
  );

  const completeFromX = useCallback(
    (x: number) => {
      if (disabled) return;
      const nextValue = valueForX(x);
      onValueChange?.(nextValue);
      onSlidingComplete?.(nextValue);
    },
    [disabled, onSlidingComplete, onValueChange, valueForX],
  );

  const gesture = useMemo(() => {
    const pan = Gesture.Pan()
      .enabled(!disabled)
      .minDistance(3)
      .runOnJS(true)
      .onBegin(event => {
        setDragging(true);
        onSlidingStart?.();
        updateFromX(event.x);
      })
      .onUpdate(event => updateFromX(event.x))
      .onEnd(event => completeFromX(event.x))
      .onFinalize(() => setDragging(false));

    const tap = Gesture.Tap()
      .enabled(!disabled)
      .maxDistance(8)
      .runOnJS(true)
      .onBegin(() => {
        setDragging(true);
        onSlidingStart?.();
      })
      .onEnd(event => completeFromX(event.x))
      .onFinalize(() => setDragging(false));

    return Gesture.Race(pan, tap);
  }, [disabled, completeFromX, onSlidingStart, updateFromX]);

  const adjustValue = (direction: 1 | -1) => {
    if (disabled) return;
    const nextValue = clamp(
      normalizedValue + step * direction,
      minimumValue,
      maximumValue,
    );
    onValueChange?.(nextValue);
    onSlidingComplete?.(nextValue);
  };

  const onLayout = (event: LayoutChangeEvent) => {
    setWidth(event.nativeEvent.layout.width);
  };

  return (
    <GestureDetector gesture={gesture}>
      <View
        accessible
        accessibilityActions={[
          { name: 'increment', label: `Increase ${accessibilityLabel}` },
          { name: 'decrement', label: `Decrease ${accessibilityLabel}` },
        ]}
        accessibilityLabel={accessibilityLabel}
        accessibilityRole="adjustable"
        accessibilityState={{ disabled }}
        accessibilityValue={{
          min: minimumValue,
          max: maximumValue,
          now: Math.round(normalizedValue),
          text: accessibilityText ?? `${Math.round(normalizedValue)} percent`,
        }}
        onAccessibilityAction={event => {
          if (event.nativeEvent.actionName === 'increment') adjustValue(1);
          if (event.nativeEvent.actionName === 'decrement') adjustValue(-1);
        }}
        onLayout={onLayout}
        style={[styles.root, disabled && styles.disabled]}
      >
        <View
          pointerEvents="none"
          style={[
            styles.track,
            theme.isDark ? styles.trackDark : styles.trackLight,
          ]}
        >
          <View
            style={[
              styles.fill,
              {
                backgroundColor: theme.colors.accent,
                width: `${progress * 100}%`,
              },
            ]}
          />
        </View>

        <Animated.View
          pointerEvents="none"
          style={[
            styles.thumb,
            {
              left: thumbX,
              transform: [{ scale: thumbScale }],
            },
          ]}
        >
          <GlassView
            effect="clear"
            interactive
            materialSettings={{
              opticalIntensity: 72,
              transparency: 92,
              surfaceLiquidity: 100,
            }}
            variant="control"
            style={[
              styles.thumbGlass,
              theme.isDark ? styles.thumbGlassDark : styles.thumbGlassLight,
            ]}
          />
        </Animated.View>
      </View>
    </GestureDetector>
  );
}

const styles = StyleSheet.create({
  root: {
    height: 56,
    justifyContent: 'center',
    width: '100%',
  },
  track: {
    borderRadius: TRACK_HEIGHT / 2,
    height: TRACK_HEIGHT,
    marginHorizontal: THUMB_TOUCH_WIDTH / 2,
    overflow: 'hidden',
  },
  trackDark: { backgroundColor: 'rgba(255,255,255,0.13)' },
  trackLight: { backgroundColor: 'rgba(7,8,10,0.18)' },
  fill: {
    borderRadius: TRACK_HEIGHT / 2,
    height: TRACK_HEIGHT,
  },
  thumb: {
    alignItems: 'center',
    height: THUMB_TOUCH_HEIGHT,
    justifyContent: 'center',
    position: 'absolute',
    width: THUMB_TOUCH_WIDTH,
  },
  thumbGlass: {
    borderRadius: THUMB_VISUAL_HEIGHT / 2,
    height: THUMB_VISUAL_HEIGHT,
    shadowOffset: { width: 0, height: 4 },
    shadowRadius: 12,
    width: THUMB_VISUAL_WIDTH,
  },
  thumbGlassDark: {
    backgroundColor: 'rgba(255,255,255,0.035)',
    borderColor: 'rgba(255,255,255,0.34)',
    shadowOpacity: 0.26,
  },
  thumbGlassLight: {
    backgroundColor: 'rgba(255,255,255,0.10)',
    borderColor: 'rgba(17,18,22,0.22)',
    shadowOpacity: 0.16,
  },
  disabled: { opacity: 0.45 },
});
