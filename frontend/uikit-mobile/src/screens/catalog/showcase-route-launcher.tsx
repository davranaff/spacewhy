import { useCallback, useMemo } from 'react';
import {
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { ArrowUpRight, Play } from 'lucide-react-native';

import {
  openExpandedPlayer,
  openShowcase,
} from '@/app/navigation/navigation-ref';
import {
  SHOWCASE_ROUTE_DESCRIPTORS,
  type ShowcaseRouteName,
} from '@/features/showcase';
import { useAppTheme } from '@/shared/theme';
import { GlassView } from '@/shared/ui';

type ShowcaseRouteLauncherProps = {
  routes?: readonly ShowcaseRouteName[];
  includePlayer?: boolean;
  title?: string;
};

export const ShowcaseRouteLauncher = ({
  routes,
  includePlayer = false,
  title = 'Native showcases',
}: ShowcaseRouteLauncherProps) => {
  const theme = useAppTheme();
  const selectedRoutes = useMemo(
    () =>
      routes
        ? SHOWCASE_ROUTE_DESCRIPTORS.filter(descriptor =>
            routes.includes(descriptor.name),
          )
        : SHOWCASE_ROUTE_DESCRIPTORS,
    [routes],
  );
  const openRoute = useCallback(
    (routeName: ShowcaseRouteName) => openShowcase(routeName),
    [],
  );

  return (
    <View style={styles.section}>
      <Text
        accessibilityRole="header"
        style={[theme.typography.title, { color: theme.colors.text }]}
      >
        {title}
      </Text>
      <Text style={[theme.typography.body, { color: theme.colors.textMuted }]}>
        Production-minded native adaptations of the Spacewhy web flows.
      </Text>
      <ScrollView
        contentContainerStyle={styles.routes}
        horizontal
        showsHorizontalScrollIndicator={false}
      >
        {selectedRoutes.map(descriptor => (
          <Pressable
            accessibilityHint={descriptor.description}
            accessibilityLabel={`Open ${descriptor.title}`}
            accessibilityRole="button"
            key={descriptor.name}
            onPress={() => openRoute(descriptor.name)}
            style={({ pressed }) => [
              styles.pressable,
              pressed && Platform.OS === 'ios' && styles.pressed,
            ]}
          >
            <GlassView variant="control" style={styles.routeChip}>
              <Text
                numberOfLines={1}
                style={[theme.typography.label, { color: theme.colors.text }]}
              >
                {descriptor.title}
              </Text>
              <ArrowUpRight color={theme.colors.textMuted} size={17} />
            </GlassView>
          </Pressable>
        ))}
        {includePlayer ? (
          <Pressable
            accessibilityHint="Opens the native audio player showcase"
            accessibilityLabel="Open player"
            accessibilityRole="button"
            onPress={openExpandedPlayer}
            style={({ pressed }) => [
              styles.pressable,
              pressed && Platform.OS === 'ios' && styles.pressed,
            ]}
          >
            <GlassView variant="control" style={styles.routeChip}>
              <Text
                style={[theme.typography.label, { color: theme.colors.text }]}
              >
                Player
              </Text>
              <Play color={theme.colors.accent} size={17} />
            </GlassView>
          </Pressable>
        ) : null}
      </ScrollView>
    </View>
  );
};

const styles = StyleSheet.create({
  section: {
    gap: 8,
  },
  routes: {
    gap: 8,
    paddingVertical: 4,
  },
  pressable: {
    borderRadius: 18,
    minHeight: 48,
  },
  pressed: {
    opacity: 0.72,
  },
  routeChip: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: 8,
    minHeight: 48,
    paddingHorizontal: 14,
  },
});
