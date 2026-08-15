import { Platform } from 'react-native';

import type { DockMode } from '@/widgets/dock/dock-state';

export const DOCK_MIN_TARGET = Platform.select({ ios: 44, default: 48 }) ?? 48;
export const DOCK_EDGE_GAP = 8;
export const DOCK_HORIZONTAL_GUTTER = 12;
export const DOCK_NAVIGATION_HEIGHT = 64;
export const DOCK_COMPACT_HEIGHT = 52;
export const DOCK_PLAYER_HEIGHT = 72;
export const DOCK_EXPANDED_HEIGHT = 112;

export const getDockSurfaceHeight = (mode: DockMode): number => {
  switch (mode) {
    case 'compact':
    case 'contextual':
      return DOCK_COMPACT_HEIGHT;
    case 'mini-player':
      return DOCK_PLAYER_HEIGHT;
    case 'expanded-player':
      return DOCK_EXPANDED_HEIGHT;
    case 'navigation':
      return DOCK_NAVIGATION_HEIGHT;
  }
};

export const getDockContentInset = (
  mode: DockMode,
  bottomSafeArea: number,
): number =>
  getDockSurfaceHeight(mode) + Math.max(bottomSafeArea, DOCK_EDGE_GAP) + 12;

export const getPlayerAwareDockContentInset = (
  bottomSafeArea: number,
  showMiniPlayer: boolean,
): number =>
  getDockContentInset('navigation', bottomSafeArea) +
  (showMiniPlayer ? getDockContentInset('mini-player', 0) : 0);
