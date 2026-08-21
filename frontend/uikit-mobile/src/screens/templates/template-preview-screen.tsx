import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import {
  useNavigation,
  useRoute,
  type RouteProp,
} from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { ChevronLeft } from 'lucide-react-native';

import type { OverviewStackParamList } from '@/app/navigation/types';
import {
  CatalogBackdrop,
  CatalogScreenHeader,
  DemoSurface,
  catalogLayout,
} from '@/features/catalog';
import {
  DashboardTemplatePreview,
  getDashboardTemplate,
} from '@/features/templates';
import { useAppTheme } from '@/shared/theme';
import { GlassView } from '@/shared/ui';

type Navigation = NativeStackNavigationProp<OverviewStackParamList>;

export function TemplatePreviewScreen() {
  const theme = useAppTheme();
  const insets = useSafeAreaInsets();
  const navigation = useNavigation<Navigation>();
  const route =
    useRoute<RouteProp<OverviewStackParamList, 'TemplatePreview'>>();
  const template = getDashboardTemplate(route.params.templateId);

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
        {template ? (
          <>
            <CatalogScreenHeader
              description={template.description}
              eyebrow={`${template.family} · ${template.kind}`}
              title={template.title}
              trailing={<BackButton onPress={navigation.goBack} />}
            />
            <DashboardTemplatePreview template={template} />
            <View style={styles.contract}>
              <Text
                style={[
                  theme.typography.label,
                  { color: theme.colors.textMuted },
                ]}
              >
                WEB PARITY CONTRACT
              </Text>
              <Text
                style={[theme.typography.body, { color: theme.colors.text }]}
              >
                This screen preserves the web route purpose and core states
                while reorganizing its layout, gestures and information density
                for a phone.
              </Text>
              <GlassView variant="control" style={styles.pathPill}>
                <Text
                  numberOfLines={1}
                  style={[styles.path, { color: theme.colors.textMuted }]}
                >
                  {template.webPath}
                </Text>
              </GlassView>
            </View>
          </>
        ) : (
          <DemoSurface
            title="Template not found"
            description="This native template link may be outdated."
          />
        )}
      </ScrollView>
    </CatalogBackdrop>
  );
}

function BackButton({ onPress }: { onPress: () => void }) {
  const theme = useAppTheme();
  return (
    <Pressable
      accessibilityLabel="Back to template library"
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

const styles = StyleSheet.create({
  backButton: {
    alignItems: 'center',
    borderRadius: 18,
    height: 48,
    justifyContent: 'center',
    overflow: 'hidden',
    width: 48,
  },
  contract: { gap: 7, marginTop: 8, padding: 8 },
  pathPill: {
    alignSelf: 'flex-start',
    borderRadius: 14,
    maxWidth: '100%',
    paddingHorizontal: 10,
    paddingVertical: 7,
  },
  path: { fontFamily: 'Courier', fontSize: 12, lineHeight: 16 },
});
