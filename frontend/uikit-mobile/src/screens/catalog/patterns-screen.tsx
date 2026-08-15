import { PATTERN_EXAMPLES } from '@/features/catalog';
import { CatalogListScreen } from '@/screens/catalog/catalog-list-screen';
import { ShowcaseRouteLauncher } from '@/screens/catalog/showcase-route-launcher';

export function PatternsScreen() {
  return (
    <CatalogListScreen
      description="Composed native interactions for navigation, validation and view state."
      examples={PATTERN_EXAMPLES}
      headerAccessory={<ShowcaseRouteLauncher includePlayer />}
      previewRoute="PatternPreview"
      title="Patterns"
    />
  );
}
