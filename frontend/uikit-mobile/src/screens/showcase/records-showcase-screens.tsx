import { useMemo, useState } from 'react';
import {
  FlatList,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import { CheckCircle2, ChevronRight, Search } from 'lucide-react-native';

import {
  ShowcaseButton,
  ShowcaseField,
  ShowcaseHeader,
  ShowcasePage,
  ShowcaseStatePanel,
  ShowcaseStateStrip,
} from '@/features/showcase/components/showcase-primitives';
import {
  filterShowcaseRecords,
  SHOWCASE_RECORDS,
} from '@/features/showcase/data/showcase-data';
import {
  validateShowcaseForm,
  type ShowcaseFormValues,
} from '@/features/showcase/lib/showcase-validation';
import type {
  ShowcasePreviewState,
  ShowcaseRecord,
} from '@/features/showcase/types/showcase.types';
import { useAppTheme } from '@/shared/theme';
import { GlassView } from '@/shared/ui/glass-view';

const categories = ['All', 'Design', 'Engineering', 'Operations'] as const;

export function ShowcaseRecordsScreen({
  onOpenRecord,
}: {
  onOpenRecord?: (id: string) => void;
}) {
  const theme = useAppTheme();
  const [query, setQuery] = useState('');
  const [category, setCategory] = useState<(typeof categories)[number]>('All');
  const [previewState, setPreviewState] =
    useState<ShowcasePreviewState>('success');
  const [selection, setSelection] = useState('');
  const records = useMemo(
    () => filterShowcaseRecords(SHOWCASE_RECORDS, query, category),
    [category, query],
  );
  const data = previewState === 'success' ? records : [];

  return (
    <FlatList
      ListEmptyComponent={
        previewState === 'success' ? (
          <ShowcaseStatePanel
            emptyTitle="No matching records"
            onRetry={() => {
              setQuery('');
              setCategory('All');
            }}
            state="empty"
          />
        ) : (
          <ShowcaseStatePanel
            onRetry={() => setPreviewState('success')}
            state={previewState}
          />
        )
      }
      ListHeaderComponent={
        <View style={styles.listHeader}>
          <ShowcaseHeader
            title="Project records"
            description="Searchable, filterable and virtualized for long mobile data sets."
          />
          <ShowcaseStateStrip onChange={setPreviewState} value={previewState} />
          <View
            style={[
              styles.search,
              {
                backgroundColor: theme.colors.surface,
                borderColor: theme.colors.border,
              },
            ]}
          >
            <Search color={theme.colors.textMuted} size={19} />
            <TextInput
              accessibilityLabel="Search records"
              autoCapitalize="none"
              onChangeText={setQuery}
              placeholder="Search name, owner or status"
              placeholderTextColor={theme.colors.textMuted}
              style={[
                theme.typography.body,
                styles.searchInput,
                { color: theme.colors.text },
              ]}
              value={query}
            />
          </View>
          <FlatList
            contentContainerStyle={styles.filters}
            data={categories}
            horizontal
            keyExtractor={item => item}
            renderItem={({ item }) => (
              <Pressable
                accessibilityRole="button"
                accessibilityState={{ selected: category === item }}
                onPress={() => setCategory(item)}
                style={[
                  styles.filter,
                  {
                    backgroundColor:
                      category === item
                        ? theme.colors.accent
                        : theme.colors.surface,
                    borderColor: theme.colors.border,
                  },
                ]}
              >
                <Text
                  style={[
                    theme.typography.label,
                    {
                      color:
                        category === item
                          ? theme.colors.accentContrast
                          : theme.colors.text,
                    },
                  ]}
                >
                  {item}
                </Text>
              </Pressable>
            )}
            showsHorizontalScrollIndicator={false}
          />
          {selection ? (
            <Text
              accessibilityLiveRegion="polite"
              style={[theme.typography.label, { color: theme.colors.positive }]}
            >
              Selected {selection}
            </Text>
          ) : null}
        </View>
      }
      contentContainerStyle={[
        styles.listContent,
        { backgroundColor: theme.colors.canvas },
      ]}
      data={data}
      keyboardShouldPersistTaps="handled"
      keyExtractor={item => item.id}
      renderItem={({ item }) => (
        <Pressable
          accessibilityRole="button"
          accessibilityLabel={`${item.name}, ${item.status}`}
          onPress={() => {
            setSelection(item.name);
            onOpenRecord?.(item.id);
          }}
          style={({ pressed }) => pressed && styles.pressed}
        >
          <GlassView style={styles.recordCard} variant="surface">
            <View style={styles.recordCopy}>
              <View style={styles.recordTitle}>
                <Text
                  style={[theme.typography.title, { color: theme.colors.text }]}
                >
                  {item.name}
                </Text>
                <Text
                  style={[
                    theme.typography.label,
                    { color: theme.colors.accent },
                  ]}
                >
                  {item.status}
                </Text>
              </View>
              <Text
                style={[
                  theme.typography.body,
                  { color: theme.colors.textMuted },
                ]}
              >
                {item.id} · {item.category}
              </Text>
              <Text
                style={[
                  theme.typography.label,
                  { color: theme.colors.textMuted },
                ]}
              >
                {item.owner} · {item.updatedAt}
              </Text>
            </View>
            <ChevronRight color={theme.colors.textMuted} size={20} />
          </GlassView>
        </Pressable>
      )}
    />
  );
}

export function ShowcaseRecordDetailScreen({
  record = SHOWCASE_RECORDS[0],
  onEdit,
  topInsetHandled,
}: {
  record?: ShowcaseRecord;
  onEdit?: () => void;
  topInsetHandled?: boolean;
}) {
  const theme = useAppTheme();
  const fields = [
    ['Owner', record.owner],
    ['Category', record.category],
    ['Status', record.status],
    ['Last updated', record.updatedAt],
  ];
  return (
    <ShowcasePage topInsetHandled={topInsetHandled}>
      <ShowcaseHeader
        eyebrow={record.id}
        title={record.name}
        description="A dense web detail view reorganized into readable mobile sections."
      />
      <GlassView style={styles.heroCard} variant="floating">
        <Text
          style={[theme.typography.label, { color: theme.colors.textMuted }]}
        >
          DELIVERY PROGRESS
        </Text>
        <Text style={[theme.typography.display, { color: theme.colors.text }]}>
          {record.progress}%
        </Text>
        <View
          style={[
            styles.progressTrack,
            { backgroundColor: theme.colors.surfaceElevated },
          ]}
        >
          <View
            style={[
              styles.progressFill,
              {
                backgroundColor: theme.colors.accent,
                width: `${record.progress}%`,
              },
            ]}
          />
        </View>
      </GlassView>
      <GlassView style={styles.detailCard} variant="surface">
        {fields.map(([label, value]) => (
          <View
            key={label}
            style={[
              styles.detailRow,
              { borderBottomColor: theme.colors.border },
            ]}
          >
            <Text
              style={[
                theme.typography.label,
                { color: theme.colors.textMuted },
              ]}
            >
              {label}
            </Text>
            <Text style={[theme.typography.body, { color: theme.colors.text }]}>
              {value}
            </Text>
          </View>
        ))}
      </GlassView>
      <ShowcaseButton
        disabled={!onEdit}
        label="Edit this local record"
        onPress={onEdit ?? (() => undefined)}
      />
    </ShowcasePage>
  );
}

export function ShowcaseRecordFormScreen({
  record = SHOWCASE_RECORDS[0],
  topInsetHandled,
}: {
  record?: ShowcaseRecord;
  topInsetHandled?: boolean;
}) {
  const theme = useAppTheme();
  const [values, setValues] = useState<ShowcaseFormValues>({
    name: record.name,
    email: `${record.owner.toLowerCase().replace(/\s+/g, '.')}@spacewhy.uz`,
    description: `${record.category} workspace maintained in the local Spacewhy preview.`,
  });
  const [errors, setErrors] = useState<ReturnType<typeof validateShowcaseForm>>(
    {},
  );
  const [saved, setSaved] = useState(false);
  const update = (key: keyof ShowcaseFormValues) => (value: string) => {
    setValues(current => ({ ...current, [key]: value }));
    setSaved(false);
  };
  const submit = () => {
    const next = validateShowcaseForm(values);
    setErrors(next);
    setSaved(Object.keys(next).length === 0);
  };
  return (
    <ShowcasePage topInsetHandled={topInsetHandled}>
      <ShowcaseHeader
        eyebrow={record.id}
        title={`Edit ${record.name}`}
        description="Clear labels, inline errors and local-only success feedback."
      />
      <GlassView style={styles.form} variant="surface">
        <ShowcaseField
          error={errors.name}
          label="Project name"
          onChangeText={update('name')}
          value={values.name}
        />
        <ShowcaseField
          autoCapitalize="none"
          error={errors.email}
          keyboardType="email-address"
          label="Owner email"
          onChangeText={update('email')}
          value={values.email}
        />
        <ShowcaseField
          error={errors.description}
          label="Description"
          multiline
          onChangeText={update('description')}
          value={values.description}
        />
        <ShowcaseButton label="Validate and save locally" onPress={submit} />
        {saved ? (
          <View accessibilityLiveRegion="polite" style={styles.saved}>
            <CheckCircle2 color={theme.colors.positive} size={20} />
            <Text
              style={[theme.typography.label, { color: theme.colors.positive }]}
            >
              Saved in the local preview.
            </Text>
          </View>
        ) : null}
      </GlassView>
    </ShowcasePage>
  );
}

const styles = StyleSheet.create({
  listContent: { flexGrow: 1, gap: 10, padding: 20, paddingBottom: 120 },
  listHeader: { gap: 16, marginBottom: 8 },
  search: {
    alignItems: 'center',
    borderRadius: 16,
    borderWidth: StyleSheet.hairlineWidth,
    flexDirection: 'row',
    gap: 10,
    minHeight: 48,
    paddingHorizontal: 14,
  },
  searchInput: { flex: 1 },
  filters: { gap: 8 },
  filter: {
    alignItems: 'center',
    borderRadius: 999,
    borderWidth: StyleSheet.hairlineWidth,
    justifyContent: 'center',
    minHeight: 44,
    paddingHorizontal: 15,
  },
  recordCard: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: 10,
    minHeight: 104,
    padding: 16,
  },
  recordCopy: { flex: 1, gap: 4 },
  recordTitle: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: 8,
    justifyContent: 'space-between',
  },
  pressed: { opacity: 0.72 },
  heroCard: { gap: 10, padding: 20 },
  progressTrack: { borderRadius: 4, height: 8, overflow: 'hidden' },
  progressFill: { borderRadius: 4, height: '100%' },
  detailCard: { paddingHorizontal: 18 },
  detailRow: {
    alignItems: 'center',
    borderBottomWidth: StyleSheet.hairlineWidth,
    flexDirection: 'row',
    justifyContent: 'space-between',
    minHeight: 58,
  },
  form: { gap: 16, padding: 20 },
  saved: { alignItems: 'center', flexDirection: 'row', gap: 8 },
});
