import { Platform } from 'react-native';

import type { DockMode } from '@/widgets/dock/dock-state';

export const DOCK_MIN_TARGET = Platform.select({ ios: 44, default: 48 }) ?? 48;
export const DOCK_EDGE_GAP = 8;
export const DOCK_HORIZONTAL_GUTTER = 12;
export const DOCK_NAVIGATION_HEIGHT = 64;
export const DOCK_COMPACT_HEIGHT = 52;
export const DOCK_PLAYER_HEIGHT = 72;
export const DOCK_EXPANDED_HEIGHT = 112;
export const DOCK_BLOB_EDGE_INSET = 4;
export const DOCK_NAVIGATION_VERTICAL_INSET = 4;
export const DOCK_BLOB_VERTICAL_INSET = 1;

export type DockBlobLayout = {
  slotWidth: number;
  width: number;
  x: number;
};

export const getDockBlobLayout = (
  containerWidth: number,
  itemCount: number,
  activeIndex: number,
  size = 100,
): DockBlobLayout => {
  const safeCount = Math.max(1, itemCount);
  const safeWidth = Math.max(0, containerWidth);
  const slotWidth = safeWidth / safeCount;
  const normalizedSize = Math.min(100, Math.max(0, size)) / 100;
  const width = Math.max(
    DOCK_MIN_TARGET,
    (slotWidth - DOCK_BLOB_EDGE_INSET * 2) * normalizedSize,
  );
  const index = Math.min(safeCount - 1, Math.max(0, activeIndex));

  return {
    slotWidth,
    width,
    x: index * slotWidth + (slotWidth - width) / 2,
  };
};

export const getNearestDockBlobIndex = (
  containerWidth: number,
  itemCount: number,
  blobX: number,
  size = 100,
): number => {
  const layout = getDockBlobLayout(containerWidth, itemCount, 0, size);
  const offset = (layout.slotWidth - layout.width) / 2;
  const rawIndex = Math.round((blobX - offset) / Math.max(1, layout.slotWidth));

  return Math.min(Math.max(1, itemCount) - 1, Math.max(0, rawIndex));
};

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
