import {
  createPlayerStore,
  selectCurrentTrack,
  selectProgress,
} from '@/features/player/store/player-store';
import type {
  PlayerSnapshot,
  PlayerTrack,
} from '@/features/player/types/player.types';

const tracks: readonly PlayerTrack[] = [
  { id: 'one', title: 'One', artist: 'Artist', source: 'one.mp3' },
  { id: 'two', title: 'Two', artist: 'Artist', source: 'two.mp3' },
];

const snapshot = (overrides: Partial<PlayerSnapshot> = {}): PlayerSnapshot => ({
  queue: tracks,
  currentIndex: 0,
  status: 'idle',
  position: 0,
  duration: 0,
  error: null,
  ...overrides,
});

describe('player store', () => {
  it('clamps queue indexes and resets playback state', () => {
    const store = createPlayerStore(snapshot({ position: 24, duration: 60 }));
    store.getState().replaceQueue(tracks, 99);

    expect(store.getState().currentIndex).toBe(1);
    expect(store.getState().position).toBe(0);
    expect(store.getState().status).toBe('idle');
  });

  it('represents an empty queue explicitly', () => {
    const store = createPlayerStore(snapshot());
    store.getState().clear();

    expect(store.getState().status).toBe('empty');
    expect(store.getState().currentIndex).toBe(-1);
    expect(selectCurrentTrack(store.getState())).toBeUndefined();
  });

  it('returns a finite, bounded presentation progress', () => {
    const store = createPlayerStore(snapshot({ position: 90, duration: 60 }));
    expect(selectProgress(store.getState())).toBe(1);

    store.getState().updatePlayback({ duration: 0 });
    expect(selectProgress(store.getState())).toBe(0);
  });
});
