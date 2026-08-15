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
import {
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
  const [width, setWidth] = useState(0);
  const translateX = useRef(new Animated.Value(0)).current;
  const scale = useRef(new Animated.Value(1)).current;
  const dragOrigin = useRef(0);
  const latestX = useRef(0);
  const layout = getDockBlobLayout(width, itemCount, activeIndex);

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
          );
          moveTo(getDockBlobLayout(width, itemCount, index).x);
          if (index !== activeIndex) onSelect(index);
        })
        .onFinalize(() => setPressed(false)),
    [
      activeIndex,
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
              effect="regular"
              interactive
              materialSettings={{
                opticalIntensity: 82,
                transparency: 72,
                surfaceLiquidity: 100,
              }}
              tone="dark"
              variant="control"
              style={styles.blobGlass}
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
    bottom: 3,
    left: 0,
    position: 'absolute',
    top: 3,
    zIndex: 0,
  },
  blobGlass: {
    backgroundColor: 'rgba(255,255,255,0.085)',
    borderColor: 'rgba(255,255,255,0.30)',
    borderRadius: 999,
    flex: 1,
  },
});
