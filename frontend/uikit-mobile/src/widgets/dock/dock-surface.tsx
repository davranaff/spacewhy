import type { PropsWithChildren } from 'react';
import { useEffect, useRef } from 'react';
import {
  Animated,
  Easing,
  StyleSheet,
  View,
  type StyleProp,
  type AccessibilityRole,
  type ViewStyle,
} from 'react-native';

import { GlassView } from '@/shared/ui';
import { useAppSettingsStore } from '@/shared/settings';
import { useAppTheme } from '@/shared/theme';
import {
  DOCK_EDGE_GAP,
  DOCK_HORIZONTAL_GUTTER,
  getDockContentInset,
  getDockSurfaceHeight,
} from '@/widgets/dock/dock-layout';
import type { DockMode } from '@/widgets/dock/dock-state';
import { useReducedMotion } from '@/widgets/dock/use-reduced-motion';

type DockSurfaceProps = PropsWithChildren<{
  mode: DockMode;
  bottomSafeArea: number;
  accessibilityLabel: string;
  accessibilityRole?: AccessibilityRole;
  style?: StyleProp<ViewStyle>;
}>;

export const DockSurface = ({
  mode,
  bottomSafeArea,
  accessibilityLabel,
  accessibilityRole = 'toolbar',
  style,
  children,
}: DockSurfaceProps) => {
  const reduceMotion = useReducedMotion();
  const theme = useAppTheme();
  const dock = useAppSettingsStore(state => state.settings.dock);
  const opacity = useRef(new Animated.Value(1)).current;
  const translateY = useRef(new Animated.Value(0)).current;
  const scale = useRef(new Animated.Value(1)).current;
  const reservedHeight = getDockContentInset(mode, bottomSafeArea);
  const dockIsDark =
    dock.tone === 'dark' || (dock.tone === 'adaptive' && theme.isDark);
  const overlayAlpha = (dock.backgroundOpacity / 100) * 0.52;
  const tone = dock.tone === 'adaptive' ? 'theme' : dock.tone;
  const surfaceMaterialStyle = {
    backgroundColor: dockIsDark
      ? `rgba(3,3,5,${overlayAlpha})`
      : `rgba(255,255,255,${overlayAlpha})`,
    borderColor: dockIsDark ? 'rgba(255,255,255,0.22)' : 'rgba(17,18,22,0.18)',
  };

  useEffect(() => {
    if (reduceMotion) {
      opacity.setValue(1);
      translateY.setValue(0);
      scale.setValue(1);
      return;
    }

    opacity.stopAnimation();
    translateY.stopAnimation();
    scale.stopAnimation();
    opacity.setValue(0.72);
    translateY.setValue(4);
    scale.setValue(0.985);

    Animated.parallel([
      Animated.timing(opacity, {
        toValue: 1,
        duration: 180,
        easing: Easing.out(Easing.cubic),
        useNativeDriver: true,
      }),
      Animated.timing(translateY, {
        toValue: 0,
        duration: 180,
        easing: Easing.out(Easing.cubic),
        useNativeDriver: true,
      }),
      Animated.timing(scale, {
        toValue: 1,
        duration: 180,
        easing: Easing.out(Easing.cubic),
        useNativeDriver: true,
      }),
    ]).start();

    return () => {
      opacity.stopAnimation();
      translateY.stopAnimation();
      scale.stopAnimation();
    };
  }, [mode, opacity, reduceMotion, scale, translateY]);

  return (
    <View
      accessible={false}
      accessibilityLabel={accessibilityLabel}
      accessibilityRole={accessibilityRole}
      pointerEvents="box-none"
      style={[
        styles.reservedArea,
        { backgroundColor: theme.colors.canvas, height: reservedHeight },
      ]}
    >
      <Animated.View
        style={[
          styles.positioner,
          {
            bottom: Math.max(bottomSafeArea, DOCK_EDGE_GAP),
            height: getDockSurfaceHeight(mode),
            opacity,
            transform: [{ translateY }, { scale }],
          },
        ]}
      >
        <GlassView
          interactive
          materialSettings={{
            opticalIntensity: dock.opticalIntensity,
            transparency: dock.transparency,
            surfaceLiquidity: dock.surfaceLiquidity,
          }}
          tone={tone}
          variant="floating"
          style={[styles.surface, surfaceMaterialStyle, style]}
        >
          {children}
        </GlassView>
      </Animated.View>
    </View>
  );
};

const styles = StyleSheet.create({
  reservedArea: {
    justifyContent: 'flex-end',
    width: '100%',
  },
  positioner: {
    left: DOCK_HORIZONTAL_GUTTER,
    position: 'absolute',
    right: DOCK_HORIZONTAL_GUTTER,
  },
  surface: {
    borderRadius: 999,
    flex: 1,
  },
});
