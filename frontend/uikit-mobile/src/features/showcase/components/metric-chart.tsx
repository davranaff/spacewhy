import { StyleSheet, Text, View } from 'react-native';
import Svg, { Defs, LinearGradient, Path, Stop } from 'react-native-svg';

import { useAppTheme } from '@/shared/theme';
import { GlassView } from '@/shared/ui/glass-view';

export function MetricChart() {
  const theme = useAppTheme();
  return (
    <GlassView
      accessibilityLabel="Activity increased 18 percent this week"
      style={styles.card}
      variant="floating"
    >
      <View style={styles.heading}>
        <View>
          <Text
            style={[theme.typography.label, { color: theme.colors.textMuted }]}
          >
            WEEKLY ACTIVITY
          </Text>
          <Text
            style={[theme.typography.display, { color: theme.colors.text }]}
          >
            24.8k
          </Text>
        </View>
        <Text
          style={[theme.typography.label, { color: theme.colors.positive }]}
        >
          +18.2%
        </Text>
      </View>
      <Svg
        accessibilityRole="image"
        height={150}
        viewBox="0 0 320 150"
        width="100%"
      >
        <Defs>
          <LinearGradient id="area" x1="0" x2="0" y1="0" y2="1">
            <Stop
              offset="0"
              stopColor={theme.colors.accent}
              stopOpacity="0.38"
            />
            <Stop offset="1" stopColor={theme.colors.accent} stopOpacity="0" />
          </LinearGradient>
        </Defs>
        <Path
          d="M0 128 C35 110 52 118 80 88 C112 54 128 98 160 70 C190 43 205 64 235 37 C260 14 286 38 320 20 L320 150 L0 150 Z"
          fill="url(#area)"
        />
        <Path
          d="M0 128 C35 110 52 118 80 88 C112 54 128 98 160 70 C190 43 205 64 235 37 C260 14 286 38 320 20"
          fill="none"
          stroke={theme.colors.accent}
          strokeLinecap="round"
          strokeWidth={4}
        />
      </Svg>
    </GlassView>
  );
}

const styles = StyleSheet.create({
  card: { gap: 12, padding: 18 },
  heading: {
    alignItems: 'flex-start',
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
});
