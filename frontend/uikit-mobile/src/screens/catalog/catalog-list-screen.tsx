import { useCallback } from 'react';
import {
  FlatList,
  StyleSheet,
  Text,
  View,
  type ListRenderItem,
} from 'react-native';
import {
  useNavigation,
  type NavigationProp,
  type ParamListBase,
} from '@react-navigation/native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { Box } from 'lucide-react-native';

import { useAppTheme } from '@/shared/theme';
import {
  CatalogBackdrop,
  CatalogExampleCard,
  CatalogScreenHeader,
  catalogLayout,
  type CatalogExample,
} from '@/features/catalog';

type Props = Readonly<{
  title: string;
  description: string;
  examples: readonly CatalogExample[];
  previewRoute: string;
  emptyLabel?: string;
  headerAccessory?: React.ReactElement;
}>;

export function CatalogListScreen({
  title,
  description,
  examples,
  previewRoute,
  emptyLabel = 'No examples match this filter.',
  headerAccessory,
}: Props) {
  const theme = useAppTheme();
  const insets = useSafeAreaInsets();
  const navigation = useNavigation<NavigationProp<ParamListBase>>();

  const openExample = useCallback(
    (example: CatalogExample) => {
      navigation.navigate(previewRoute, {
        exampleId: example.id,
        title: example.title,
      });
    },
    [navigation, previewRoute],
  );

  const renderItem: ListRenderItem<CatalogExample> = useCallback(
    ({ item }) => <CatalogExampleCard example={item} onPress={openExample} />,
    [openExample],
  );

  return (
    <CatalogBackdrop>
      <FlatList
        contentContainerStyle={[
          catalogLayout.content,
          { paddingTop: Math.max(insets.top, 12) + 4 },
        ]}
        data={examples as readonly CatalogExample[]}
        initialNumToRender={8}
        ItemSeparatorComponent={ListSeparator}
        keyboardDismissMode="on-drag"
        keyboardShouldPersistTaps="handled"
        keyExtractor={item => item.id}
        ListEmptyComponent={
          <View style={styles.empty}>
            <Box color={theme.colors.textMuted} size={28} />
            <Text
              style={[theme.typography.body, { color: theme.colors.textMuted }]}
            >
              {emptyLabel}
            </Text>
          </View>
        }
        ListHeaderComponent={
          <>
            <CatalogScreenHeader description={description} title={title} />
            {headerAccessory}
            <View style={styles.headerGap} />
          </>
        }
        removeClippedSubviews
        renderItem={renderItem}
        showsVerticalScrollIndicator={false}
        windowSize={6}
      />
    </CatalogBackdrop>
  );
}

function ListSeparator() {
  return <View style={catalogLayout.listSeparator} />;
}

const styles = StyleSheet.create({
  headerGap: { height: 8 },
  empty: {
    minHeight: 220,
    padding: 24,
    alignItems: 'center',
    justifyContent: 'center',
    gap: 12,
  },
});
