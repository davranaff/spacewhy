import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react';
import {
  Animated,
  Easing,
  StyleSheet,
  View,
  type LayoutChangeEvent,
} from 'react-native';
import { Gesture, GestureDetector } from 'react-native-gesture-handler';

import { GlassView } from '@/shared/ui';
import { useAppSettingsStore } from '@/shared/settings';
import { useAppTheme } from '@/shared/theme';
import {
  DOCK_BLOB_VERTICAL_INSET,
  getDockBlobLayout,
  getNearestDockBlobIndex,
} from '@/widgets/dock/dock-layout';
import { useReducedMotion } from '@/widgets/dock/use-reduced-motion';

type DockSelectionBlobProps = {
  activeIndex: number;
  itemCount: number;
  onSelect: (index: number) => void;
  children: ReactNode;
};

export function DockSelectionBlob({
  activeIndex,
  itemCount,
  onSelect,
  children,
}: DockSelectionBlobProps) {
  const reduceMotion = useReducedMotion();
  const theme = useAppTheme();
  const dock = useAppSettingsStore(state => state.settings.dock);
  const [width, setWidth] = useState(0);
  const translateX = useRef(new Animated.Value(0)).current;
  const scale = useRef(new Animated.Value(1)).current;
  const dragOrigin = useRef(0);
  const latestX = useRef(0);
  const layout = getDockBlobLayout(
    width,
    itemCount,
    activeIndex,
    dock.blobSize,
  );
  const dockIsDark =
    dock.tone === 'dark' || (dock.tone === 'adaptive' && theme.isDark);
  const tone = dock.tone === 'adaptive' ? 'theme' : dock.tone;
  const blobGlassStyle = {
    backgroundColor: dockIsDark
      ? 'rgba(255,255,255,0.035)'
      : 'rgba(255,255,255,0.12)',
    borderColor: dockIsDark ? 'rgba(255,255,255,0.34)' : 'rgba(17,18,22,0.20)',
  };

  const moveTo = useCallback(
    (x: number, immediate = false) => {
      latestX.current = x;
      translateX.stopAnimation();

      if (immediate || reduceMotion) {
        translateX.setValue(x);
        return;
      }

      Animated.spring(translateX, {
        toValue: x,
        damping: 18,
        stiffness: 220,
        mass: 0.72,
        useNativeDriver: true,
      }).start();
    },
    [reduceMotion, translateX],
  );

  useEffect(() => {
    if (width > 0) moveTo(layout.x);
  }, [layout.x, moveTo, width]);

  const setPressed = useCallback(
    (pressed: boolean) => {
      Animated.timing(scale, {
        toValue: pressed ? 1.06 : 1,
        duration: reduceMotion ? 0 : 160,
        easing: Easing.out(Easing.cubic),
        useNativeDriver: true,
      }).start();
    },
    [reduceMotion, scale],
  );

  const maxX = Math.max(0, width - layout.width);
  const gesture = useMemo(
    () =>
      Gesture.Pan()
        .enabled(width > 0 && itemCount > 1)
        .minDistance(5)
        .runOnJS(true)
        .onBegin(() => {
          dragOrigin.current = latestX.current;
          setPressed(true);
        })
        .onUpdate(event => {
          const x = Math.min(
            maxX,
            Math.max(0, dragOrigin.current + event.translationX),
          );
          latestX.current = x;
          translateX.setValue(x);
        })
        .onEnd(() => {
          const index = getNearestDockBlobIndex(
            width,
            itemCount,
            latestX.current,
            dock.blobSize,
          );
          moveTo(getDockBlobLayout(width, itemCount, index, dock.blobSize).x);
          if (index !== activeIndex) onSelect(index);
        })
        .onFinalize(() => setPressed(false)),
    [
      activeIndex,
      dock.blobSize,
      itemCount,
      maxX,
      moveTo,
      onSelect,
      setPressed,
      translateX,
      width,
    ],
  );

  const onLayout = (event: LayoutChangeEvent) => {
    const nextWidth = event.nativeEvent.layout.width;
    setWidth(current => (current === nextWidth ? current : nextWidth));
  };

  return (
    <GestureDetector gesture={gesture}>
      <View onLayout={onLayout} style={styles.container}>
        {width > 0 ? (
          <Animated.View
            pointerEvents="none"
            style={[
              styles.blob,
              {
                width: layout.width,
                transform: [{ translateX }, { scale }],
              },
            ]}
          >
            <GlassView
              interactive
              materialSettings={{
                opticalIntensity: dock.blobIntensity,
                transparency: dock.blobTransparency,
                surfaceLiquidity: dock.blobLiquidity,
              }}
              tone={tone}
              variant="control"
              style={[styles.blobGlass, blobGlassStyle]}
            />
          </Animated.View>
        ) : null}
        {children}
      </View>
    </GestureDetector>
  );
}

const styles = StyleSheet.create({
  container: {
    alignItems: 'stretch',
    flex: 1,
    flexDirection: 'row',
    position: 'relative',
  },
  blob: {
    bottom: DOCK_BLOB_VERTICAL_INSET,
    left: 0,
    position: 'absolute',
    top: DOCK_BLOB_VERTICAL_INSET,
    zIndex: 0,
  },
  blobGlass: {
    borderRadius: 999,
    flex: 1,
  },
});
