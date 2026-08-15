import { FOUNDATION_EXAMPLES } from '@/features/catalog';
import { CatalogListScreen } from '@/screens/catalog/catalog-list-screen';

export function FoundationsScreen() {
  return (
    <CatalogListScreen
      description="Color, typography, space, iconography and material as native design tokens."
      examples={FOUNDATION_EXAMPLES}
      previewRoute="FoundationPreview"
      title="Foundations"
    />
  );
}
