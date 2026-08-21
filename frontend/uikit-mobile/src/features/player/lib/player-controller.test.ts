import { PlayerEngineUnavailableError } from '@/features/player/engine/audio-api-engine';
import {
  PlayerController,
  createPlayerController,
} from '@/features/player/lib/player-controller';
import { createPlayerStore } from '@/features/player/store/player-store';
import type {
  PlayerEngine,
  PlayerSnapshot,
  PlayerTrack,
} from '@/features/player/types/player.types';

const tracks: readonly PlayerTrack[] = [
  { id: 'one', title: 'One', artist: 'Artist', source: 'one.mp3' },
  { id: 'two', title: 'Two', artist: 'Artist', source: 'two.mp3' },
];

const initial: PlayerSnapshot = {
  queue: tracks,
  currentIndex: 0,
  status: 'idle',
  position: 0,
  duration: 0,
  error: null,
};

class FakeEngine implements PlayerEngine {
  duration = 120;
  position = 0;
  loadError: Error | null = null;
  playError: Error | null = null;
  loadedTrack: PlayerTrack | null = null;
  isPlaying = false;
  disposed = false;
  onEnded: (() => void) | null = null;

  async load(track: PlayerTrack, onEnded: () => void): Promise<number> {
    if (this.loadError) {
      throw this.loadError;
    }
    this.loadedTrack = track;
    this.onEnded = onEnded;
    return this.duration;
  }

  async play(offsetSeconds: number): Promise<void> {
    if (this.playError) {
      throw this.playError;
    }
    this.position = offsetSeconds;
    this.isPlaying = true;
  }

  async pause(): Promise<number> {
    this.isPlaying = false;
    return this.position;
  }

  async seek(offsetSeconds: number, continuePlaying: boolean): Promise<void> {
    this.position = offsetSeconds;
    this.isPlaying = continuePlaying;
  }

  getPosition(): number {
    return this.position;
  }

  async dispose(): Promise<void> {
    this.isPlaying = false;
    this.disposed = true;
  }
}

describe('PlayerController', () => {
  let controller: PlayerController | null = null;

  afterEach(async () => {
    jest.useRealTimers();
    await controller?.dispose();
    controller = null;
  });

  it('transitions only after the real engine loads and starts', async () => {
    jest.useFakeTimers();
    const engine = new FakeEngine();
    const store = createPlayerStore(initial);
    controller = createPlayerController(store, () => engine);

    await controller.play();
    expect(engine.loadedTrack?.id).toBe('one');
    expect(store.getState()).toMatchObject({
      status: 'playing',
      duration: 120,
      position: 0,
      error: null,
    });

    engine.position = 18;
    jest.advanceTimersByTime(260);
    expect(store.getState().position).toBe(18);

    await controller.pause();
    expect(store.getState()).toMatchObject({ status: 'paused', position: 18 });
  });

  it('seeks without inventing a playing state', async () => {
    const engine = new FakeEngine();
    const store = createPlayerStore(initial);
    controller = createPlayerController(store, () => engine);

    await controller.seek(999);
    expect(engine.position).toBe(120);
    expect(engine.isPlaying).toBe(false);
    expect(store.getState()).toMatchObject({ status: 'paused', position: 120 });
  });

  it('keeps playback active while moving through the queue', async () => {
    const engines: FakeEngine[] = [];
    const store = createPlayerStore(initial);
    controller = createPlayerController(store, () => {
      const engine = new FakeEngine();
      engines.push(engine);
      return engine;
    });

    await controller.play();
    await controller.next();

    expect(store.getState().currentIndex).toBe(1);
    expect(store.getState().status).toBe('playing');
    expect(engines).toHaveLength(2);
    expect(engines[0].disposed).toBe(true);
    expect(engines[1].loadedTrack?.id).toBe('two');
  });

  it('pauses actual playback when the app enters background', async () => {
    const engine = new FakeEngine();
    const store = createPlayerStore(initial);
    controller = createPlayerController(store, () => engine);

    await controller.play();
    engine.position = 9;
    await controller.handleBackground();

    expect(engine.isPlaying).toBe(false);
    expect(store.getState()).toMatchObject({ status: 'paused', position: 9 });
  });

  it('ignores a stale pause result after navigation advances the queue', async () => {
    let resolvePause: ((position: number) => void) | undefined;
    class DeferredPauseEngine extends FakeEngine {
      async pause(): Promise<number> {
        this.isPlaying = false;
        return new Promise(resolve => {
          resolvePause = resolve;
        });
      }
    }

    const firstEngine = new DeferredPauseEngine();
    const secondEngine = new FakeEngine();
    const store = createPlayerStore(initial);
    let engineIndex = 0;
    controller = createPlayerController(store, () =>
      engineIndex++ === 0 ? firstEngine : secondEngine,
    );

    await controller.play();
    const pause = controller.pause();
    const next = controller.next();
    resolvePause?.(17);
    await Promise.all([pause, next]);

    expect(store.getState()).toMatchObject({
      currentIndex: 1,
      status: 'playing',
      position: 0,
    });
  });

  it('normalizes transient playback state when the shell disposes', async () => {
    const engine = new FakeEngine();
    const store = createPlayerStore({ ...initial, status: 'loading' });
    controller = createPlayerController(store, () => engine);

    await controller.dispose();

    expect(store.getState().status).toBe('paused');
  });

  it('distinguishes native unavailability from load and playback errors', async () => {
    const unavailableStore = createPlayerStore(initial);
    controller = createPlayerController(unavailableStore, () => {
      throw new PlayerEngineUnavailableError('Audio module missing');
    });
    await controller.play();
    expect(unavailableStore.getState()).toMatchObject({
      status: 'unavailable',
      error: { code: 'engine-unavailable' },
    });
    await controller.dispose();

    const loadEngine = new FakeEngine();
    loadEngine.loadError = new Error('Network unavailable');
    const loadStore = createPlayerStore(initial);
    controller = createPlayerController(loadStore, () => loadEngine);
    await controller.play();
    expect(loadStore.getState()).toMatchObject({
      status: 'error',
      error: { code: 'load-failed' },
    });
    await controller.dispose();

    const playEngine = new FakeEngine();
    playEngine.playError = new Error('Output route unavailable');
    const playStore = createPlayerStore(initial);
    controller = createPlayerController(playStore, () => playEngine);
    await controller.play();
    expect(playStore.getState()).toMatchObject({
      status: 'error',
      error: { code: 'playback-failed' },
    });
  });
});
