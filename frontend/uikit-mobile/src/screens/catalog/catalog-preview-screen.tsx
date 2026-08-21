import { ScrollView, StyleSheet, Text, View } from 'react-native';
import { useRoute } from '@react-navigation/native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { useAppTheme } from '@/shared/theme';
import {
  CatalogBackdrop,
  CatalogExamplePreview,
  CatalogScreenHeader,
  DemoSurface,
  catalogLayout,
  getCatalogExample,
  type CatalogExampleId,
} from '@/features/catalog';

export function CatalogPreviewScreen() {
  const theme = useAppTheme();
  const insets = useSafeAreaInsets();
  const route = useRoute();
  const params = route.params as
    | { exampleId?: string; title?: string }
    | undefined;
  const example = getCatalogExample(params?.exampleId ?? '');

  return (
    <CatalogBackdrop>
      <ScrollView
        contentContainerStyle={[
          catalogLayout.content,
          { paddingTop: Math.max(insets.top, 12) + 4 },
        ]}
        keyboardDismissMode="interactive"
        keyboardShouldPersistTaps="handled"
        showsVerticalScrollIndicator={false}
      >
        {example ? (
          <>
            <CatalogScreenHeader
              description={example.description}
              eyebrow={example.group.replace('-', ' ')}
              title={params?.title ?? example.title}
            />
            <CatalogExamplePreview exampleId={example.id as CatalogExampleId} />
            <View style={styles.notes}>
              <Text
                style={[
                  theme.typography.label,
                  { color: theme.colors.textMuted },
                ]}
              >
                NATIVE CONTRACT
              </Text>
              <Text
                style={[theme.typography.body, { color: theme.colors.text }]}
              >
                Semantic accessibility, minimum 44 pt targets, light and dark
                themes, reduced-motion awareness and predictable platform
                fallbacks.
              </Text>
            </View>
          </>
        ) : (
          <DemoSurface
            title="Example not found"
            description="This catalog link may be outdated."
          />
        )}
      </ScrollView>
    </CatalogBackdrop>
  );
}

const styles = StyleSheet.create({
  notes: { padding: 8, gap: 6, marginTop: 4 },
});
