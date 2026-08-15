import {
  SHOWCASE_RECORDS,
  SHOWCASE_ROUTE_DESCRIPTORS,
  filterShowcaseRecords,
} from './showcase-data';

describe('showcase route and record contracts', () => {
  it('keeps every route name unique and grouped', () => {
    const names = SHOWCASE_ROUTE_DESCRIPTORS.map(route => route.name);
    expect(new Set(names).size).toBe(names.length);
    expect(names).toHaveLength(10);
  });

  it('filters records by query and category', () => {
    expect(
      filterShowcaseRecords(SHOWCASE_RECORDS, 'maya', 'All').map(
        record => record.id,
      ),
    ).toEqual(['sw-1048']);
    expect(
      filterShowcaseRecords(SHOWCASE_RECORDS, '', 'Operations'),
    ).toHaveLength(2);
    expect(filterShowcaseRecords(SHOWCASE_RECORDS, 'not-found', 'All')).toEqual(
      [],
    );
  });
});
