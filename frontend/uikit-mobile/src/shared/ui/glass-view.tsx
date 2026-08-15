import {
  LiquidGlassView,
  isLiquidGlassSupported,
} from '@callstack/liquid-glass';
import { BlurView } from '@react-native-community/blur';
import { forwardRef, useRef, type PropsWithChildren } from 'react';
import {
  Platform,
  StyleSheet,
  View,
  type StyleProp,
  type ViewProps,
  type ViewStyle,
} from 'react-native';

import { useReducedTransparency } from '@/shared/accessibility/use-reduced-transparency';
import { useAppSettingsStore, type GlassSettings } from '@/shared/settings';
import { createAppTheme, useAppTheme } from '@/shared/theme';

import { resolveGlassMaterial, type GlassVariant } from './glass-material';

export interface GlassViewProps extends ViewProps {
  variant?: GlassVariant;
  tone?: 'theme' | 'dark';
  interactive?: boolean;
  effect?: 'clear' | 'regular';
  reducedTransparency?: boolean;
  materialSettings?: Partial<GlassSettings>;
}

type OuterGlassStyle = Pick<
  ViewStyle,
  | 'alignSelf'
  | 'aspectRatio'
  | 'bottom'
  | 'display'
  | 'elevation'
  | 'end'
  | 'flex'
  | 'flexBasis'
  | 'flexGrow'
  | 'flexShrink'
  | 'height'
  | 'left'
  | 'margin'
  | 'marginBottom'
  | 'marginEnd'
  | 'marginHorizontal'
  | 'marginLeft'
  | 'marginRight'
  | 'marginStart'
  | 'marginTop'
  | 'marginVertical'
  | 'maxHeight'
  | 'maxWidth'
  | 'minHeight'
  | 'minWidth'
  | 'opacity'
  | 'position'
  | 'right'
  | 'shadowColor'
  | 'shadowOffset'
  | 'shadowOpacity'
  | 'shadowRadius'
  | 'start'
  | 'top'
  | 'transform'
  | 'transformOrigin'
  | 'width'
  | 'zIndex'
>;

function splitGlassStyle(style: StyleProp<ViewStyle>): {
  outerStyle: OuterGlassStyle;
  surfaceStyle: ViewStyle;
} {
  const flattened = StyleSheet.flatten(style) ?? {};
  const {
    alignSelf,
    aspectRatio,
    bottom,
    display,
    elevation,
    end,
    flex,
    flexBasis,
    flexGrow,
    flexShrink,
    height,
    left,
    margin,
    marginBottom,
    marginEnd,
    marginHorizontal,
    marginLeft,
    marginRight,
    marginStart,
    marginTop,
    marginVertical,
    maxHeight,
    maxWidth,
    minHeight,
    minWidth,
    opacity,
    position,
    right,
    shadowColor,
    shadowOffset,
    shadowOpacity,
    shadowRadius,
    start,
    top,
    transform,
    transformOrigin,
    width,
    zIndex,
    ...surfaceStyle
  } = flattened;

  return {
    outerStyle: {
      alignSelf,
      aspectRatio,
      bottom,
      display,
      elevation,
      end,
      flex,
      flexBasis,
      flexGrow,
      flexShrink,
      height,
      left,
      margin,
      marginBottom,
      marginEnd,
      marginHorizontal,
      marginLeft,
      marginRight,
      marginStart,
      marginTop,
      marginVertical,
      maxHeight,
      maxWidth,
      minHeight,
      minWidth,
      opacity,
      position,
      right,
      shadowColor,
      shadowOffset,
      shadowOpacity,
      shadowRadius,
      start,
      top,
      transform,
      transformOrigin,
      width,
      zIndex,
    },
    surfaceStyle,
  };
}

export const GlassView = forwardRef<View, PropsWithChildren<GlassViewProps>>(
  function GlassViewImpl(
    {
      children,
      variant = 'surface',
      tone = 'theme',
      interactive = false,
      effect,
      reducedTransparency,
      materialSettings,
      style,
      ...viewProps
    },
    ref,
  ) {
    const theme = useAppTheme();
    const materialTheme = tone === 'dark' ? createAppTheme('dark') : theme;
    const glassSettings = useAppSettingsStore(state => state.settings.glass);
    const systemReducedTransparency = useReducedTransparency();
    const shouldReduceTransparency =
      reducedTransparency ?? systemReducedTransparency;
    const initialInteractive = useRef(interactive).current;
    const resolvedGlassSettings = {
      ...glassSettings,
      ...materialSettings,
    };
    const material = resolveGlassMaterial(materialTheme, {
      variant,
      ...resolvedGlassSettings,
    });
    const { outerStyle, surfaceStyle } = splitGlassStyle(style);
    const hostStyle = [
      styles.shadowHost,
      {
        shadowColor: '#000000',
        shadowOpacity: material.shadowOpacity,
        shadowRadius: material.shadowRadius,
      },
      outerStyle,
    ];
    const sharedSurfaceStyle = [
      styles.container,
      {
        borderColor: material.borderColor,
        borderRadius: material.borderRadius,
      },
      surfaceStyle,
    ];

    if (
      Platform.OS === 'ios' &&
      isLiquidGlassSupported &&
      !shouldReduceTransparency
    ) {
      return (
        <View ref={ref} {...viewProps} style={hostStyle}>
          <LiquidGlassView
            colorScheme={materialTheme.mode}
            effect={
              effect ??
              (resolvedGlassSettings.opticalIntensity >= 55
                ? 'regular'
                : 'clear')
            }
            interactive={initialInteractive}
            style={sharedSurfaceStyle}
            tintColor={material.nativeTintColor}
          >
            {children}
          </LiquidGlassView>
        </View>
      );
    }

    return (
      <View ref={ref} {...viewProps} style={hostStyle}>
        <View
          style={[
            sharedSurfaceStyle,
            shouldReduceTransparency && {
              backgroundColor: material.reducedTransparencyColor,
            },
          ]}
        >
          {!shouldReduceTransparency && Platform.OS === 'ios' ? (
            <BlurView
              blurAmount={material.blurAmount}
              blurType={materialTheme.isDark ? 'dark' : 'light'}
              pointerEvents="none"
              reducedTransparencyFallbackColor={
                material.reducedTransparencyColor
              }
              style={StyleSheet.absoluteFill}
            />
          ) : null}

          {!shouldReduceTransparency && Platform.OS === 'android' ? (
            <View
              pointerEvents="none"
              style={[
                StyleSheet.absoluteFill,
                { backgroundColor: material.matteColor },
              ]}
            />
          ) : null}

          {children}
        </View>
      </View>
    );
  },
);

const styles = StyleSheet.create({
  shadowHost: {
    elevation: 8,
    shadowOffset: { width: 0, height: 8 },
  },
  container: {
    alignSelf: 'stretch',
    borderWidth: StyleSheet.hairlineWidth,
    flexGrow: 1,
    overflow: 'hidden',
  },
});

export type { GlassVariant } from './glass-material';
