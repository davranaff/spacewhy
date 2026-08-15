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
      contentContainerStyle={[
        styles.content,
        { backgroundColor: theme.colors.canvas },
      ]}
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
              style={[theme.typography.body, { color: theme.colors.textMuted }]}
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
  );
}

const styles = StyleSheet.create({
  content: { gap: 10, padding: 20, paddingBottom: 120 },
  headerContent: { gap: 20, marginBottom: 4 },
  metrics: { flexDirection: 'row', gap: 8 },
  metric: { flex: 1, gap: 6, minHeight: 126, padding: 12 },
  metricValue: { fontSize: 23 },
  delta: { alignItems: 'center', flexDirection: 'row', gap: 3 },
  record: { alignItems: 'center', flexDirection: 'row', gap: 12, padding: 16 },
  recordCopy: { flex: 1, gap: 3 },
});
