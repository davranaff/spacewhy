import { useMemo, useState } from 'react';

import {
  COMPONENT_EXAMPLES,
  CatalogSearch,
  filterCatalogExamples,
} from '@/features/catalog';
import { CatalogListScreen } from '@/screens/catalog/catalog-list-screen';

export function ComponentsScreen() {
  const [query, setQuery] = useState('');
  const examples = useMemo(() => {
    if (!query.trim()) {
      return COMPONENT_EXAMPLES;
    }

    const componentIds = new Set(COMPONENT_EXAMPLES.map(example => example.id));
    return filterCatalogExamples(query).filter(example =>
      componentIds.has(example.id),
    );
  }, [query]);

  return (
    <CatalogListScreen
      description="Reachable controls, forms, feedback, data display and surface primitives."
      emptyLabel="No native component matches that search."
      examples={examples}
      headerAccessory={<CatalogSearch onChangeText={setQuery} value={query} />}
      previewRoute="ComponentPreview"
      title="Components"
    />
  );
}
