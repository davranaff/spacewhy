import {
  CATALOG_EXAMPLES,
  CATALOG_SECTIONS,
  COMPONENT_EXAMPLES,
  FOUNDATION_EXAMPLES,
  PATTERN_EXAMPLES,
  filterCatalogExamples,
  getCatalogExample,
} from '@/features/catalog/data/catalog-data';

describe('native catalog data', () => {
  it('keeps stable, unique example identifiers', () => {
    const ids = CATALOG_EXAMPLES.map(example => example.id);

    expect(CATALOG_EXAMPLES).toHaveLength(22);
    expect(new Set(ids).size).toBe(ids.length);
  });

  it('covers every catalog group without dropping examples', () => {
    expect(CATALOG_SECTIONS).toHaveLength(7);
    expect(CATALOG_SECTIONS.every(section => section.examples.length > 0)).toBe(
      true,
    );
    expect(
      CATALOG_SECTIONS.flatMap(section => section.examples).map(
        example => example.id,
      ),
    ).toEqual(CATALOG_EXAMPLES.map(example => example.id));
  });

  it('exposes focused screen collections', () => {
    expect(
      FOUNDATION_EXAMPLES.every(item => item.group === 'foundations'),
    ).toBe(true);
    expect(COMPONENT_EXAMPLES.some(item => item.group === 'forms')).toBe(true);
    expect(COMPONENT_EXAMPLES.some(item => item.group === 'data-display')).toBe(
      true,
    );
    expect(PATTERN_EXAMPLES.map(item => item.id)).toEqual([
      'form-flow',
      'contextual-dock',
      'tabs-segments',
    ]);
    expect(COMPONENT_EXAMPLES.map(item => item.id)).toContain(
      'dock-indicators',
    );
  });

  it('searches title, category and keywords case-insensitively', () => {
    expect(filterCatalogExamples('GLASS').map(item => item.id)).toContain(
      'glass-material',
    );
    expect(filterCatalogExamples('checkbox').map(item => item.id)).toEqual([
      'selection-controls',
    ]);
    expect(filterCatalogExamples('data-display').map(item => item.id)).toEqual([
      'avatars-lists',
      'metrics',
      'virtualized-list',
    ]);
  });

  it('resolves deep-link examples safely', () => {
    expect(getCatalogExample('buttons')?.title).toBe('Buttons');
    expect(getCatalogExample('missing')).toBeUndefined();
  });
});
