import { FOUNDATION_EXAMPLES } from '@/features/catalog';
import { CatalogListScreen } from '@/screens/catalog/catalog-list-screen';

export function FoundationsScreen() {
  return (
    <CatalogListScreen
      description="Colors, typography, shadows, grid and icons from the complete web UI kit."
      examples={FOUNDATION_EXAMPLES}
      previewRoute="FoundationPreview"
      title="Foundations"
    />
  );
}
