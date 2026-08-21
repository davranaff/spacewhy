import { useStore } from 'zustand';
import { createStore, type StoreApi } from 'zustand/vanilla';

import { PLAYER_DEMO_QUEUE } from '@/features/player/data/demo-queue';
import type {
  PlayerError,
  PlayerSnapshot,
  PlayerStatus,
  PlayerTrack,
} from '@/features/player/types/player.types';

export interface PlayerStoreState extends PlayerSnapshot {
  replaceQueue: (queue: readonly PlayerTrack[], startIndex?: number) => void;
  selectIndex: (index: number) => void;
  updatePlayback: (update: {
    status?: PlayerStatus;
    position?: number;
    duration?: number;
    error?: PlayerError | null;
  }) => void;
  clear: () => void;
}

const initialSnapshot: PlayerSnapshot = {
  queue: PLAYER_DEMO_QUEUE,
  currentIndex: 0,
  status: 'idle',
  position: 0,
  duration: 0,
  error: null,
};

const clampIndex = (index: number, length: number): number =>
  length === 0 ? -1 : Math.min(length - 1, Math.max(0, Math.floor(index)));

export function createPlayerStore(
  snapshot: PlayerSnapshot = initialSnapshot,
): StoreApi<PlayerStoreState> {
  return createStore<PlayerStoreState>()(set => ({
    ...snapshot,
    replaceQueue: (queue, startIndex = 0) =>
      set({
        queue,
        currentIndex: clampIndex(startIndex, queue.length),
        status: queue.length ? 'idle' : 'empty',
        position: 0,
        duration: 0,
        error: null,
      }),
    selectIndex: index =>
      set(state => ({
        currentIndex: clampIndex(index, state.queue.length),
        status: state.queue.length ? 'idle' : 'empty',
        position: 0,
        duration: 0,
        error: null,
      })),
    updatePlayback: update => set(update),
    clear: () =>
      set({
        queue: [],
        currentIndex: -1,
        status: 'empty',
        position: 0,
        duration: 0,
        error: null,
      }),
  }));
}

export const playerStore = createPlayerStore();

export function usePlayerStore<T>(selector: (state: PlayerStoreState) => T): T {
  return useStore(playerStore, selector);
}

export const selectCurrentTrack = (
  state: PlayerStoreState,
): PlayerTrack | undefined => state.queue[state.currentIndex];

export const selectProgress = (state: PlayerStoreState): number => {
  if (!Number.isFinite(state.duration) || state.duration <= 0) {
    return 0;
  }

  return Math.min(1, Math.max(0, state.position / state.duration));
};
