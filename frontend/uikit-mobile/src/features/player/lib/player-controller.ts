import type { StoreApi } from 'zustand/vanilla';

import {
  PlayerEngineUnavailableError,
  createAudioApiPlayerEngine,
} from '@/features/player/engine/audio-api-engine';
import {
  playerStore,
  selectCurrentTrack,
  type PlayerStoreState,
} from '@/features/player/store/player-store';
import type {
  PlayerEngine,
  PlayerEngineFactory,
  PlayerError,
  PlayerTrack,
} from '@/features/player/types/player.types';

const POSITION_POLL_MS = 250;

const readableError = (error: unknown, fallback: string): string => {
  if (error instanceof Error && error.message.trim()) {
    return error.message;
  }
  return fallback;
};

export class PlayerController {
  private engine: PlayerEngine | null = null;
  private loadedTrackId: string | null = null;
  private operation = 0;
  private ticker: ReturnType<typeof setInterval> | null = null;

  constructor(
    private readonly store: StoreApi<PlayerStoreState>,
    private readonly engineFactory: PlayerEngineFactory,
  ) {}

  async setQueue(
    queue: readonly PlayerTrack[],
    startIndex = 0,
    autoplay = false,
  ): Promise<void> {
    await this.resetEngine();
    this.store.getState().replaceQueue(queue, startIndex);
    if (autoplay && queue.length) {
      await this.play();
    }
  }

  async play(): Promise<void> {
    const state = this.store.getState();
    const track = selectCurrentTrack(state);
    if (!track || state.status === 'loading' || state.status === 'playing') {
      return;
    }

    const operation = ++this.operation;
    try {
      await this.ensureLoaded(track, operation);
    } catch (error) {
      if (operation === this.operation) {
        this.fail(error, 'load-failed');
      }
      return;
    }

    if (operation !== this.operation || !this.engine) {
      return;
    }

    const nextState = this.store.getState();
    const offset =
      nextState.position >= nextState.duration ? 0 : nextState.position;
    try {
      await this.engine.play(offset);
    } catch (error) {
      if (operation === this.operation) {
        this.fail(error, 'playback-failed');
      }
      return;
    }

    if (operation !== this.operation) {
      return;
    }
    this.store.getState().updatePlayback({
      status: 'playing',
      position: offset,
      error: null,
    });
    this.startTicker();
  }

  async pause(): Promise<void> {
    if (this.store.getState().status !== 'playing' || !this.engine) {
      return;
    }

    const operation = ++this.operation;
    this.stopTicker();
    try {
      const position = await this.engine.pause();
      if (operation !== this.operation) {
        return;
      }
      this.store.getState().updatePlayback({ status: 'paused', position });
    } catch (error) {
      if (operation === this.operation) {
        this.fail(error, 'playback-failed');
      }
    }
  }

  async togglePlayback(): Promise<void> {
    if (this.store.getState().status === 'playing') {
      await this.pause();
      return;
    }
    await this.play();
  }

  async seek(position: number): Promise<void> {
    const state = this.store.getState();
    const track = selectCurrentTrack(state);
    if (!track) {
      return;
    }

    const operation = ++this.operation;
    const wasPlaying = state.status === 'playing';
    this.stopTicker();
    try {
      await this.ensureLoaded(track, operation);
      if (operation !== this.operation || !this.engine) {
        return;
      }
      const duration = this.store.getState().duration;
      const safePosition = Number.isFinite(position)
        ? Math.min(duration, Math.max(0, position))
        : 0;
      await this.engine.seek(safePosition, wasPlaying);
      if (operation !== this.operation) {
        return;
      }
      this.store.getState().updatePlayback({
        position: safePosition,
        status: wasPlaying ? 'playing' : 'paused',
        error: null,
      });
      if (wasPlaying) {
        this.startTicker();
      }
    } catch (error) {
      if (operation === this.operation) {
        this.fail(error, 'playback-failed');
      }
    }
  }

  async next(): Promise<void> {
    await this.move(1);
  }

  async previous(): Promise<void> {
    const state = this.store.getState();
    if (state.position > 3) {
      await this.seek(0);
      return;
    }
    await this.move(-1);
  }

  async selectTrack(index: number, autoplay = true): Promise<void> {
    const queue = this.store.getState().queue;
    if (index < 0 || index >= queue.length) {
      return;
    }

    const shouldPlay = autoplay && this.store.getState().status !== 'empty';
    await this.invalidateLoadedTrack();
    this.store.getState().selectIndex(index);
    if (shouldPlay) {
      await this.play();
    }
  }

  async retry(): Promise<void> {
    await this.invalidateLoadedTrack();
    this.store.getState().updatePlayback({ status: 'idle', error: null });
    await this.play();
  }

  async handleBackground(): Promise<void> {
    if (this.store.getState().status === 'playing') {
      await this.pause();
    }
  }

  async close(): Promise<void> {
    await this.resetEngine();
    this.store.getState().clear();
  }

  async dispose(): Promise<void> {
    await this.resetEngine();
    const state = this.store.getState();
    if (state.status === 'playing' || state.status === 'loading') {
      state.updatePlayback({ status: 'paused' });
    }
  }

  private async move(delta: -1 | 1): Promise<void> {
    const state = this.store.getState();
    if (!state.queue.length) {
      return;
    }

    const shouldContinue =
      state.status === 'playing' || state.status === 'loading';
    const nextIndex =
      (state.currentIndex + delta + state.queue.length) % state.queue.length;
    await this.invalidateLoadedTrack();
    this.store.getState().selectIndex(nextIndex);
    if (shouldContinue) {
      await this.play();
    }
  }

  private async ensureLoaded(
    track: PlayerTrack,
    operation: number,
  ): Promise<void> {
    if (this.loadedTrackId === track.id && this.engine) {
      return;
    }

    this.store.getState().updatePlayback({
      status: 'loading',
      position: 0,
      duration: 0,
      error: null,
    });
    const engine = this.engine ?? this.engineFactory();
    this.engine = engine;
    const duration = await engine.load(track, () => {
      this.handleTrackEnded().catch(error =>
        this.fail(error, 'playback-failed'),
      );
    });

    if (operation !== this.operation) {
      return;
    }
    this.loadedTrackId = track.id;
    this.store.getState().updatePlayback({
      status: 'paused',
      position: 0,
      duration,
      error: null,
    });
  }

  private async handleTrackEnded(): Promise<void> {
    this.stopTicker();
    this.store.getState().updatePlayback({
      position: this.store.getState().duration,
      status: 'paused',
    });
    await this.move(1);
    await this.play();
  }

  private startTicker(): void {
    this.stopTicker();
    this.ticker = setInterval(() => {
      if (!this.engine || this.store.getState().status !== 'playing') {
        return;
      }
      this.store.getState().updatePlayback({
        position: this.engine.getPosition(),
      });
    }, POSITION_POLL_MS);
  }

  private stopTicker(): void {
    if (this.ticker) {
      clearInterval(this.ticker);
      this.ticker = null;
    }
  }

  private async invalidateLoadedTrack(): Promise<void> {
    ++this.operation;
    this.stopTicker();
    this.loadedTrackId = null;
    if (this.engine) {
      await this.engine.dispose().catch(() => undefined);
      this.engine = null;
    }
  }

  private async resetEngine(): Promise<void> {
    await this.invalidateLoadedTrack();
  }

  private fail(
    error: unknown,
    fallbackCode: 'load-failed' | 'playback-failed',
  ): void {
    this.stopTicker();
    this.loadedTrackId = null;
    const failedEngine = this.engine;
    this.engine = null;
    failedEngine?.dispose().catch(() => undefined);
    const unavailable = error instanceof PlayerEngineUnavailableError;
    const playerError: PlayerError = {
      code: unavailable ? 'engine-unavailable' : fallbackCode,
      message: readableError(
        error,
        unavailable
          ? 'Native playback is unavailable.'
          : 'Audio playback failed.',
      ),
    };
    this.store.getState().updatePlayback({
      status: unavailable ? 'unavailable' : 'error',
      error: playerError,
    });
  }
}

export const createPlayerController = (
  store: StoreApi<PlayerStoreState>,
  engineFactory: PlayerEngineFactory,
): PlayerController => new PlayerController(store, engineFactory);

export const playerController = createPlayerController(
  playerStore,
  createAudioApiPlayerEngine,
);
