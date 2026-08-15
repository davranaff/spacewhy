import { FlatList, StyleSheet, Text, View } from 'react-native';
import { ArrowDownRight, ArrowUpRight } from 'lucide-react-native';

import { MetricChart } from '@/features/showcase/components/metric-chart';
import { ShowcaseHeader } from '@/features/showcase/components/showcase-primitives';
import { SHOWCASE_RECORDS } from '@/features/showcase/data/showcase-data';
import { useAppTheme } from '@/shared/theme';
import { GlassView } from '@/shared/ui/glass-view';

const metrics = [
  { label: 'Active users', value: '18,765', delta: '+2.6%', up: true },
  { label: 'Installed', value: '4,876', delta: '+0.2%', up: true },
  { label: 'Downloads', value: '678', delta: '-0.1%', up: false },
] as const;

export function ShowcaseDashboardScreen() {
  const theme = useAppTheme();
  return (
    <View style={[styles.screen, { backgroundColor: theme.colors.canvas }]}>
      <View
        pointerEvents="none"
        style={[
          styles.backdropOrb,
          styles.backdropOrbTop,
          theme.isDark ? styles.backdropTopDark : styles.backdropTopLight,
        ]}
      />
      <View
        pointerEvents="none"
        style={[
          styles.backdropOrb,
          styles.backdropOrbBottom,
          theme.isDark ? styles.backdropBottomDark : styles.backdropBottomLight,
        ]}
      />
      <FlatList
        ListHeaderComponent={
          <View style={styles.headerContent}>
            <ShowcaseHeader
              title="Command overview"
              description="The web dashboard hierarchy, distilled for one-handed mobile scanning."
            />
            <View style={styles.metrics}>
              {metrics.map(metric => (
                <GlassView
                  key={metric.label}
                  style={styles.metric}
                  variant="surface"
                >
                  <Text
                    style={[
                      theme.typography.label,
                      { color: theme.colors.textMuted },
                    ]}
                  >
                    {metric.label}
                  </Text>
                  <Text
                    style={[
                      theme.typography.title,
                      styles.metricValue,
                      { color: theme.colors.text },
                    ]}
                  >
                    {metric.value}
                  </Text>
                  <View style={styles.delta}>
                    {metric.up ? (
                      <ArrowUpRight color={theme.colors.positive} size={16} />
                    ) : (
                      <ArrowDownRight color={theme.colors.negative} size={16} />
                    )}
                    <Text
                      style={[
                        theme.typography.label,
                        {
                          color: metric.up
                            ? theme.colors.positive
                            : theme.colors.negative,
                        },
                      ]}
                    >
                      {metric.delta}
                    </Text>
                  </View>
                </GlassView>
              ))}
            </View>
            <MetricChart />
            <Text
              accessibilityRole="header"
              style={[theme.typography.title, { color: theme.colors.text }]}
            >
              Recent projects
            </Text>
          </View>
        }
        contentContainerStyle={styles.content}
        data={SHOWCASE_RECORDS.slice(0, 4)}
        keyExtractor={item => item.id}
        renderItem={({ item }) => (
          <GlassView
            accessibilityLabel={`${item.name}, ${item.status}, ${item.progress} percent`}
            style={styles.record}
            variant="surface"
          >
            <View style={styles.recordCopy}>
              <Text
                style={[theme.typography.title, { color: theme.colors.text }]}
              >
                {item.name}
              </Text>
              <Text
                style={[
                  theme.typography.body,
                  { color: theme.colors.textMuted },
                ]}
              >
                {item.owner} · {item.updatedAt}
              </Text>
            </View>
            <Text
              style={[theme.typography.label, { color: theme.colors.accent }]}
            >
              {item.progress}%
            </Text>
          </GlassView>
        )}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1 },
  backdropOrb: {
    borderRadius: 180,
    height: 360,
    opacity: 0.38,
    position: 'absolute',
    width: 360,
  },
  backdropOrbTop: { right: -220, top: -150 },
  backdropOrbBottom: { bottom: 80, left: -240, opacity: 0.28 },
  backdropTopDark: { backgroundColor: '#2B2D32' },
  backdropTopLight: { backgroundColor: '#C5C8CE' },
  backdropBottomDark: { backgroundColor: '#111419' },
  backdropBottomLight: { backgroundColor: '#E0E2E6' },
  content: { gap: 10, padding: 20, paddingBottom: 120 },
  headerContent: { gap: 20, marginBottom: 4 },
  metrics: { flexDirection: 'row', gap: 8 },
  metric: { flex: 1, gap: 6, minHeight: 126, padding: 12 },
  metricValue: { fontSize: 23 },
  delta: { alignItems: 'center', flexDirection: 'row', gap: 3 },
  record: { alignItems: 'center', flexDirection: 'row', gap: 12, padding: 16 },
  recordCopy: { flex: 1, gap: 3 },
});
