import type { LinkingOptions } from '@react-navigation/native';

import {
  DOCK_DESTINATIONS,
  ROOT_LINK_PATHS,
  ROOT_LINK_PREFIXES,
  SHOWCASE_LINK_PATHS,
} from '@/app/navigation/navigation-contracts';
import type { RootStackParamList } from '@/app/navigation/types';

const tabPaths = Object.fromEntries(
  DOCK_DESTINATIONS.map(destination => [
    destination.route,
    { path: destination.path },
  ]),
);

export const navigationLinking: LinkingOptions<RootStackParamList> = {
  prefixes: [...ROOT_LINK_PREFIXES],
  config: {
    screens: {
      Catalog: {
        screens: tabPaths,
      },
      CatalogPreview: ROOT_LINK_PATHS.CatalogPreview,
      ExpandedPlayer: ROOT_LINK_PATHS.ExpandedPlayer,
      ...SHOWCASE_LINK_PATHS,
    },
  },
};
