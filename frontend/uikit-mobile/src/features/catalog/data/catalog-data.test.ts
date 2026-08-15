import {
  CATALOG_EXAMPLES,
  CATALOG_SECTIONS,
  COMPONENT_EXAMPLES,
  FOUNDATION_EXAMPLES,
  PATTERN_EXAMPLES,
  filterCatalogExamples,
  getCatalogExample,
} from '@/features/catalog/data/catalog-data';
import { CATALOG_ICON_REGISTRY } from '@/features/catalog/data/catalog-icon-registry';

describe('native catalog data', () => {
  it('keeps stable, unique example identifiers', () => {
    const ids = CATALOG_EXAMPLES.map(example => example.id);

    expect(CATALOG_EXAMPLES).toHaveLength(54);
    expect(new Set(ids).size).toBe(ids.length);
  });

  it('provides the original web catalog icon for every example', () => {
    expect(Object.keys(CATALOG_ICON_REGISTRY).sort()).toEqual(
      CATALOG_EXAMPLES.map(example => example.id).sort(),
    );
  });

  it('covers every catalog group without dropping examples', () => {
    expect(CATALOG_SECTIONS).toHaveLength(3);
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
    expect(COMPONENT_EXAMPLES).toHaveLength(29);
    expect(COMPONENT_EXAMPLES.every(item => item.group === 'mui')).toBe(true);
    expect(PATTERN_EXAMPLES).toHaveLength(20);
    expect(PATTERN_EXAMPLES.every(item => item.group === 'extra')).toBe(true);
  });

  it('searches title, category and keywords case-insensitively', () => {
    expect(filterCatalogExamples('GLASS').map(item => item.id)).toContain(
      'shadows',
    );
    expect(filterCatalogExamples('checkbox').map(item => item.id)).toEqual([
      'checkbox',
    ]);
    expect(filterCatalogExamples('extra')).toHaveLength(20);
  });

  it('resolves deep-link examples safely', () => {
    expect(getCatalogExample('buttons')?.title).toBe('Buttons');
    expect(getCatalogExample('missing')).toBeUndefined();
  });
});
