import { useCallback } from 'react';
import {
  FlatList,
  StyleSheet,
  Text,
  View,
  type ListRenderItem,
} from 'react-native';
import { useNavigation } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import {
  ArrowUpRight,
  CircleAlert,
  Layers3,
  ListTree,
  MousePointer2,
  Palette,
  PanelsTopLeft,
  Sparkles,
  TextCursorInput,
  type LucideIcon,
} from 'lucide-react-native';

import { useAppTheme } from '@/shared/theme';
import { GlassView } from '@/shared/ui/glass-view';
import type { OverviewStackParamList } from '@/app/navigation/types';
import {
  CATALOG_EXAMPLES,
  CATALOG_SECTIONS,
  CatalogBackdrop,
  CatalogScreenHeader,
  DemoButton,
  catalogLayout,
  type CatalogSection,
} from '@/features/catalog';
import { ShowcaseRouteLauncher } from '@/screens/catalog/showcase-route-launcher';

const groupIcons: Record<CatalogSection['id'], LucideIcon> = {
  foundations: Palette,
  controls: MousePointer2,
  forms: TextCursorInput,
  feedback: CircleAlert,
  'data-display': ListTree,
  surfaces: Layers3,
  patterns: PanelsTopLeft,
};

export function OverviewScreen() {
  const theme = useAppTheme();
  const insets = useSafeAreaInsets();
  const navigation =
    useNavigation<NativeStackNavigationProp<OverviewStackParamList>>();

  const openFeatured = useCallback(() => {
    navigation.navigate('OverviewPreview', {
      exampleId: 'glass-material',
      title: 'Liquid glass',
    });
  }, [navigation]);

  const renderSection: ListRenderItem<CatalogSection> = useCallback(
    ({ item }) => {
      const Icon = groupIcons[item.id];
      return (
        <View
          style={[
            styles.groupCard,
            {
              backgroundColor: theme.colors.surface,
              borderColor: theme.colors.border,
            },
          ]}
        >
          <View
            style={[
              styles.groupIcon,
              { backgroundColor: theme.colors.surfaceElevated },
            ]}
          >
            <Icon color={theme.colors.accent} size={21} />
          </View>
          <View style={styles.flex}>
            <Text
              style={[
                theme.typography.title,
                styles.groupTitle,
                { color: theme.colors.text },
              ]}
            >
              {item.title}
            </Text>
            <Text
              numberOfLines={2}
              style={[
                styles.groupDescription,
                { color: theme.colors.textMuted },
              ]}
            >
              {item.description}
            </Text>
          </View>
          <Text
            style={[theme.typography.label, { color: theme.colors.textMuted }]}
          >
            {item.examples.length}
          </Text>
        </View>
      );
    },
    [theme],
  );

  return (
    <CatalogBackdrop>
      <FlatList
        contentContainerStyle={[
          catalogLayout.content,
          { paddingTop: Math.max(insets.top, 12) + 4 },
        ]}
        data={CATALOG_SECTIONS as readonly CatalogSection[]}
        initialNumToRender={7}
        ItemSeparatorComponent={Separator}
        keyExtractor={item => item.id}
        ListHeaderComponent={
          <View style={styles.headerStack}>
            <CatalogScreenHeader
              description="A native, production-minded companion to the complete Spacewhy web UI kit."
              title="Build with clarity"
            />
            <GlassView variant="surface" style={styles.heroCard}>
              <View
                style={[
                  styles.heroIcon,
                  { backgroundColor: theme.colors.accent },
                ]}
              >
                <Sparkles color={theme.colors.accentContrast} size={24} />
              </View>
              <Text
                style={[theme.typography.title, { color: theme.colors.text }]}
              >
                Truthful liquid glass
              </Text>
              <Text
                style={[
                  theme.typography.body,
                  { color: theme.colors.textMuted },
                ]}
              >
                Native material where available, graceful fallbacks everywhere,
                and independent optical controls.
              </Text>
              <DemoButton label="Explore material" onPress={openFeatured} />
            </GlassView>
            <View style={styles.statsRow}>
              <Stat value={String(CATALOG_EXAMPLES.length)} label="examples" />
              <Stat value="2" label="themes" />
              <Stat value="44+" label="touch pt" />
            </View>
            <ShowcaseRouteLauncher
              includePlayer
              routes={['ShowcaseDashboard', 'ShowcaseRecords', 'ShowcaseMail']}
              title="Featured native flows"
            />
            <View style={styles.sectionTitleRow}>
              <Text
                accessibilityRole="header"
                style={[theme.typography.title, { color: theme.colors.text }]}
              >
                Catalog map
              </Text>
              <ArrowUpRight color={theme.colors.textMuted} size={19} />
            </View>
          </View>
        }
        renderItem={renderSection}
        showsVerticalScrollIndicator={false}
      />
    </CatalogBackdrop>
  );
}

function Stat({ value, label }: { value: string; label: string }) {
  const theme = useAppTheme();
  return (
    <View
      style={[
        styles.stat,
        {
          backgroundColor: theme.colors.surface,
          borderColor: theme.colors.border,
        },
      ]}
    >
      <Text style={[theme.typography.title, { color: theme.colors.text }]}>
        {value}
      </Text>
      <Text style={[styles.statLabel, { color: theme.colors.textMuted }]}>
        {label}
      </Text>
    </View>
  );
}

function Separator() {
  return <View style={catalogLayout.listSeparator} />;
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  headerStack: { gap: 16, paddingBottom: 12 },
  heroCard: { borderRadius: 28, padding: 20, gap: 12 },
  heroIcon: {
    width: 48,
    height: 48,
    borderRadius: 17,
    alignItems: 'center',
    justifyContent: 'center',
  },
  statsRow: { flexDirection: 'row', gap: 9 },
  stat: {
    flex: 1,
    minHeight: 78,
    padding: 12,
    borderRadius: 19,
    borderWidth: StyleSheet.hairlineWidth,
    justifyContent: 'center',
    gap: 2,
  },
  statLabel: { fontSize: 11, lineHeight: 15 },
  sectionTitleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingTop: 6,
  },
  groupCard: {
    minHeight: 92,
    borderRadius: 22,
    borderWidth: StyleSheet.hairlineWidth,
    padding: 14,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  groupIcon: {
    width: 44,
    height: 44,
    borderRadius: 15,
    alignItems: 'center',
    justifyContent: 'center',
  },
  groupTitle: { fontSize: 17, lineHeight: 21 },
  groupDescription: { fontSize: 13, lineHeight: 18, marginTop: 3 },
});
