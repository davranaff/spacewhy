import { EXTRA_EXAMPLES } from '@/features/catalog';
import { CatalogListScreen } from '@/screens/catalog/catalog-list-screen';

export function PatternsScreen() {
  return (
    <CatalogListScreen
      description="All 20 advanced component routes from the web kit, adapted for native interaction."
      examples={EXTRA_EXAMPLES}
      previewRoute="PatternPreview"
      title="Extra components"
    />
  );
}
