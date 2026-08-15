import {
  DOCK_DESTINATIONS,
  ROOT_LINK_PATHS,
  ROOT_LINK_PREFIXES,
  SHOWCASE_LINK_PATHS,
  getDockDestination,
} from '../../src/app/navigation/navigation-contracts';
import { SHOWCASE_ROUTE_DESCRIPTORS } from '../../src/features/showcase';

describe('mobile navigation contracts', () => {
  it('keeps no more than five stable, unique primary destinations', () => {
    const routes = DOCK_DESTINATIONS.map(destination => destination.route);
    const paths = DOCK_DESTINATIONS.map(destination => destination.path);

    expect(DOCK_DESTINATIONS).toHaveLength(5);
    expect(routes).toEqual([
      'OverviewTab',
      'FoundationsTab',
      'ComponentsTab',
      'PatternsTab',
      'SettingsTab',
    ]);
    expect(new Set(routes).size).toBe(routes.length);
    expect(new Set(paths).size).toBe(paths.length);
  });

  it('keeps every destination discoverable and screen-reader labelled', () => {
    DOCK_DESTINATIONS.forEach(destination => {
      expect(destination.label.trim()).not.toBe('');
      expect(destination.accessibilityHint.trim()).not.toBe('');
      expect(getDockDestination(destination.route)).toBe(destination);
    });
  });

  it('uses only app and owned web prefixes for deep links', () => {
    expect(ROOT_LINK_PREFIXES).toEqual(['spacewhyuikit://']);
    expect(ROOT_LINK_PATHS.CatalogPreview).toContain(':exampleId');
    expect(ROOT_LINK_PATHS.ExpandedPlayer).toBe('player');
  });

  it('keeps every showcase route deep-linkable with unique paths', () => {
    const descriptorNames = SHOWCASE_ROUTE_DESCRIPTORS.map(
      descriptor => descriptor.name,
    );
    const pathNames = Object.keys(SHOWCASE_LINK_PATHS);
    const paths = Object.values(SHOWCASE_LINK_PATHS);

    expect(pathNames).toEqual(descriptorNames);
    expect(new Set(paths).size).toBe(paths.length);
    expect(SHOWCASE_LINK_PATHS.ShowcaseRecordDetail).toContain(':recordId');
  });
});
