export {
  CATALOG_EXAMPLES,
  CATALOG_SECTIONS,
  COMPONENT_EXAMPLES,
  FOUNDATION_EXAMPLES,
  PATTERN_EXAMPLES,
  filterCatalogExamples,
  getCatalogExample,
} from '@/features/catalog/data/catalog-data';

export type {
  CatalogExample,
  CatalogExampleId,
  CatalogGroup,
  CatalogPreviewProps,
  CatalogSection,
} from '@/features/catalog/types/catalog.types';

export { CatalogExamplePreview } from '@/features/catalog/components/catalog-example-preview';
export {
  CatalogBackdrop,
  CatalogExampleCard,
  CatalogScreenHeader,
  CatalogSearch,
  CatalogSectionHeading,
  DemoButton,
  DemoSurface,
  catalogLayout,
} from '@/features/catalog/components/catalog-primitives';
