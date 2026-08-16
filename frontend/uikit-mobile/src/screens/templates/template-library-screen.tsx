import { useMemo, useState } from 'react';
import {
  Pressable,
  SectionList,
  StyleSheet,
  Text,
  View,
  type SectionListRenderItem,
} from 'react-native';
import { useNavigation } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import {
  BarChart3,
  ChevronLeft,
  ChevronRight,
  FileText,
  LayoutDashboard,
  PanelsTopLeft,
  Rows3,
  Settings2,
  UserRound,
  type LucideIcon,
} from 'lucide-react-native';

import type { OverviewStackParamList } from '@/app/navigation/types';
import {
  CatalogBackdrop,
  CatalogScreenHeader,
  CatalogSearch,
  catalogLayout,
} from '@/features/catalog';
import {
  DASHBOARD_TEMPLATE_SECTIONS,
  filterDashboardTemplates,
  type DashboardTemplate,
  type DashboardTemplateKind,
  type DashboardTemplateSection,
} from '@/features/templates';
import { useAppTheme } from '@/shared/theme';
import { GlassView } from '@/shared/ui';

const kindIcons: Readonly<Record<DashboardTemplateKind, LucideIcon>> = {
  overview: BarChart3,
  profile: UserRound,
  cards: PanelsTopLeft,
  list: Rows3,
  detail: FileText,
  form: FileText,
  account: Settings2,
  'file-manager': PanelsTopLeft,
  mail: PanelsTopLeft,
  chat: PanelsTopLeft,
  calendar: PanelsTopLeft,
  kanban: PanelsTopLeft,
  permission: Settings2,
  blank: LayoutDashboard,
};

type Navigation = NativeStackNavigationProp<OverviewStackParamList>;

export function TemplateLibraryScreen() {
  const theme = useAppTheme();
  const insets = useSafeAreaInsets();
  const navigation = useNavigation<Navigation>();
  const [query, setQuery] = useState('');
  const sections = useMemo(() => {
    const matches = new Set(
      filterDashboardTemplates(query).map(template => template.id),
    );
    return DASHBOARD_TEMPLATE_SECTIONS.map(section => ({
      ...section,
      data: section.templates.filter(template => matches.has(template.id)),
    })).filter(section => section.data.length);
  }, [query]);

  const renderItem: SectionListRenderItem<
    DashboardTemplate,
    DashboardTemplateSection & { data: readonly DashboardTemplate[] }
  > = ({ item }) => {
    const Icon = kindIcons[item.kind];
    return (
      <Pressable
        accessibilityHint={`Opens the native ${item.title} template`}
        accessibilityLabel={`${item.title}. ${item.description}`}
        accessibilityRole="button"
        onPress={() =>
          navigation.navigate('TemplatePreview', { templateId: item.id })
        }
        style={({ pressed }) => [
          styles.cardPressable,
          pressed && styles.pressed,
        ]}
      >
        <GlassView interactive variant="surface" style={styles.card}>
          <View
            style={[
              styles.cardIcon,
              { backgroundColor: theme.colors.surfaceElevated },
            ]}
          >
            <Icon color={theme.colors.text} size={22} />
          </View>
          <View style={styles.flex}>
            <Text
              style={[
                theme.typography.title,
                styles.cardTitle,
                { color: theme.colors.text },
              ]}
            >
              {item.title}
            </Text>
            <Text
              numberOfLines={2}
              style={[styles.description, { color: theme.colors.textMuted }]}
            >
              {item.description}
            </Text>
            <Text style={[styles.path, { color: theme.colors.textMuted }]}>
              {item.webPath}
            </Text>
          </View>
          <ChevronRight color={theme.colors.textMuted} size={20} />
        </GlassView>
      </Pressable>
    );
  };

  return (
    <CatalogBackdrop>
      <SectionList
        contentContainerStyle={[
          catalogLayout.content,
          { paddingTop: Math.max(insets.top, 12) + 4 },
        ]}
        ItemSeparatorComponent={ItemSeparator}
        keyExtractor={item => item.id}
        keyboardDismissMode="interactive"
        keyboardShouldPersistTaps="handled"
        ListEmptyComponent={
          <GlassView variant="surface" style={styles.empty}>
            <Text
              style={[theme.typography.title, { color: theme.colors.text }]}
            >
              No matching templates
            </Text>
            <Text
              style={[theme.typography.body, { color: theme.colors.textMuted }]}
            >
              Try a page family such as invoice, product, overview or workspace.
            </Text>
          </GlassView>
        }
        ListHeaderComponent={
          <View style={styles.headerStack}>
            <CatalogScreenHeader
              description="All 41 dashboard routes from the web UI kit, rebuilt as reachable native layouts."
              eyebrow="Web → Native"
              title="Dashboard templates"
              trailing={<BackButton onPress={navigation.goBack} />}
            />
            <CatalogSearch onChangeText={setQuery} value={query} />
            <View style={styles.statsRow}>
              <TemplateStat label="routes" value="41" />
              <TemplateStat label="families" value="15" />
              <TemplateStat label="dead links" value="0" />
            </View>
          </View>
        }
        renderItem={renderItem}
        renderSectionHeader={({ section }) => (
          <View style={styles.sectionHeader}>
            <Text
              accessibilityRole="header"
              style={[theme.typography.title, { color: theme.colors.text }]}
            >
              {section.title}
            </Text>
            <Text
              style={[styles.description, { color: theme.colors.textMuted }]}
            >
              {section.description}
            </Text>
          </View>
        )}
        sections={sections}
        showsVerticalScrollIndicator={false}
        stickySectionHeadersEnabled={false}
      />
    </CatalogBackdrop>
  );
}

function BackButton({ onPress }: { onPress: () => void }) {
  const theme = useAppTheme();
  return (
    <Pressable
      accessibilityLabel="Back to overview"
      accessibilityRole="button"
      onPress={onPress}
      style={styles.backButton}
    >
      <GlassView
        pointerEvents="none"
        style={StyleSheet.absoluteFill}
        variant="control"
      />
      <ChevronLeft color={theme.colors.text} size={22} />
    </Pressable>
  );
}

function TemplateStat({ value, label }: { value: string; label: string }) {
  const theme = useAppTheme();
  return (
    <GlassView variant="control" style={styles.stat}>
      <Text style={[theme.typography.title, { color: theme.colors.text }]}>
        {value}
      </Text>
      <Text style={[styles.path, { color: theme.colors.textMuted }]}>
        {label}
      </Text>
    </GlassView>
  );
}

function ItemSeparator() {
  return <View style={catalogLayout.listSeparator} />;
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  headerStack: { gap: 14, paddingBottom: 18 },
  backButton: {
    alignItems: 'center',
    borderRadius: 18,
    height: 48,
    justifyContent: 'center',
    overflow: 'hidden',
    width: 48,
  },
  statsRow: { flexDirection: 'row', gap: 8 },
  stat: { borderRadius: 18, flex: 1, gap: 1, minHeight: 70, padding: 12 },
  sectionHeader: { gap: 3, paddingBottom: 10, paddingTop: 18 },
  cardPressable: { borderRadius: 22 },
  pressed: { opacity: 0.74 },
  card: {
    alignItems: 'center',
    borderRadius: 22,
    flexDirection: 'row',
    gap: 12,
    minHeight: 104,
    padding: 14,
  },
  cardIcon: {
    alignItems: 'center',
    borderRadius: 17,
    height: 48,
    justifyContent: 'center',
    width: 48,
  },
  cardTitle: { fontSize: 17, lineHeight: 22 },
  description: { fontSize: 13, lineHeight: 18 },
  path: { fontSize: 11, lineHeight: 15, marginTop: 3 },
  empty: { borderRadius: 24, gap: 8, marginTop: 24, padding: 20 },
});
