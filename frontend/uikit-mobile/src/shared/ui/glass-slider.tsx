import Slider from '@react-native-community/slider';

import { useAppTheme } from '@/shared/theme';

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

/**
 * Keeps the native UISlider geometry and interaction material used by the
 * original Spacewhy mobile build. On iOS 26 the system owns the idle thumb and
 * its larger liquid-glass pressed state; drawing another thumb above it breaks
 * both the proportions and the native transition.
 */
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

  return (
    <Slider
      accessibilityLabel={accessibilityLabel}
      accessibilityValue={{
        min: minimumValue,
        max: maximumValue,
        now: Math.round(value),
        text: accessibilityText ?? `${Math.round(value)} percent`,
      }}
      disabled={disabled}
      maximumTrackTintColor={theme.colors.border}
      maximumValue={maximumValue}
      minimumTrackTintColor={theme.colors.accent}
      minimumValue={minimumValue}
      onSlidingComplete={onSlidingComplete}
      onSlidingStart={onSlidingStart}
      onValueChange={onValueChange}
      step={step}
      thumbTintColor={theme.colors.text}
      value={value}
    />
  );
}
