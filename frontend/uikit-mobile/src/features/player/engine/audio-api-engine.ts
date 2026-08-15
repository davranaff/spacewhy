import type {
  PlayerEngine,
  PlayerTrack,
} from '@/features/player/types/player.types';

type AudioApi = typeof import('react-native-audio-api');
type AudioContextInstance = InstanceType<AudioApi['AudioContext']>;
type AudioBufferInstance = Awaited<
  ReturnType<AudioContextInstance['decodeAudioData']>
>;
type AudioSourceInstance = ReturnType<
  AudioContextInstance['createBufferSource']
>;

export class PlayerEngineUnavailableError extends Error {
  constructor(
    message = 'Native audio playback is unavailable on this device.',
  ) {
    super(message);
    this.name = 'PlayerEngineUnavailableError';
  }
}

const loadAudioApi = (): AudioApi => {
  try {
    // Delayed evaluation lets the feature render an unavailable state when the
    // native module was not linked instead of crashing the application shell.
    return require('react-native-audio-api') as AudioApi;
  } catch (error) {
    const detail =
      error instanceof Error ? error.message : 'Unknown native error';
    throw new PlayerEngineUnavailableError(
      `Native audio module could not initialize. ${detail}`,
    );
  }
};

export class AudioApiPlayerEngine implements PlayerEngine {
  private audioApi: AudioApi | null = null;
  private context: AudioContextInstance | null = null;
  private buffer: AudioBufferInstance | null = null;
  private source: AudioSourceInstance | null = null;
  private duration = 0;
  private offset = 0;
  private startedAt = 0;
  private isPlaying = false;
  private sourceGeneration = 0;
  private onEnded: (() => void) | null = null;

  async load(track: PlayerTrack, onEnded: () => void): Promise<number> {
    await this.ensureContext();
    this.stopSource();
    this.buffer = null;
    this.duration = 0;
    this.offset = 0;
    this.onEnded = onEnded;

    if (!this.context) {
      throw new PlayerEngineUnavailableError();
    }

    let buffer: AudioBufferInstance;
    try {
      buffer = await this.context.decodeAudioData(track.source);
    } catch (error) {
      await this.dispose().catch(() => undefined);
      throw error;
    }
    if (!Number.isFinite(buffer.duration) || buffer.duration <= 0) {
      throw new Error('The audio source decoded without a valid duration.');
    }

    this.buffer = buffer;
    this.duration = buffer.duration;
    return buffer.duration;
  }

  async play(offsetSeconds: number): Promise<void> {
    await this.ensureContext();
    if (!this.context || !this.buffer) {
      throw new Error('Load a track before starting playback.');
    }

    const resumed = await this.context.resume();
    if (resumed === false) {
      throw new PlayerEngineUnavailableError(
        'The system audio session could not resume.',
      );
    }

    this.stopSource();
    this.offset = this.clampPosition(offsetSeconds);
    const source = this.context.createBufferSource();
    source.buffer = this.buffer;
    source.connect(this.context.destination);
    const generation = ++this.sourceGeneration;
    source.onEnded = () => {
      if (generation !== this.sourceGeneration || !this.isPlaying) {
        return;
      }

      this.isPlaying = false;
      this.offset = this.duration;
      this.source = null;
      this.onEnded?.();
    };
    source.start(0, this.offset);
    this.source = source;
    this.startedAt = this.context.currentTime;
    this.isPlaying = true;
  }

  async pause(): Promise<number> {
    const position = this.getPosition();
    this.stopSource();
    this.offset = position;
    if (this.context?.state === 'running') {
      await this.context.suspend();
    }
    return position;
  }

  async seek(offsetSeconds: number, continuePlaying: boolean): Promise<void> {
    const nextOffset = this.clampPosition(offsetSeconds);
    this.stopSource();
    this.offset = nextOffset;

    if (continuePlaying) {
      await this.play(nextOffset);
    }
  }

  getPosition(): number {
    if (!this.isPlaying || !this.context) {
      return this.clampPosition(this.offset);
    }

    return this.clampPosition(
      this.offset + (this.context.currentTime - this.startedAt),
    );
  }

  async dispose(): Promise<void> {
    this.stopSource();
    this.buffer = null;
    this.onEnded = null;

    const context = this.context;
    const audioApi = this.audioApi;
    this.context = null;
    this.audioApi = null;
    this.duration = 0;
    this.offset = 0;

    let closeError: unknown;
    try {
      if (context && context.state !== 'closed') {
        await context.close();
      }
    } catch (error) {
      closeError = error;
    } finally {
      if (audioApi) {
        await audioApi.AudioManager.setAudioSessionActivity(false).catch(
          () => false,
        );
      }
    }

    if (closeError) {
      throw closeError;
    }
  }

  private async ensureContext(): Promise<void> {
    if (this.context && this.context.state !== 'closed') {
      return;
    }

    const audioApi = loadAudioApi();
    audioApi.AudioManager.setAudioSessionOptions({
      iosCategory: 'playback',
      iosMode: 'default',
      iosNotifyOthersOnDeactivation: true,
    });
    const activated = await audioApi.AudioManager.setAudioSessionActivity(true);
    if (!activated) {
      throw new PlayerEngineUnavailableError(
        'The system audio session is not available.',
      );
    }

    this.audioApi = audioApi;
    try {
      this.context = new audioApi.AudioContext();
    } catch (error) {
      this.audioApi = null;
      await audioApi.AudioManager.setAudioSessionActivity(false).catch(
        () => false,
      );
      throw error;
    }
  }

  private stopSource(): void {
    this.isPlaying = false;
    this.sourceGeneration += 1;
    if (this.source) {
      this.source.onEnded = null;
      try {
        this.source.stop();
      } catch {
        // A source may already have ended; cleanup remains idempotent.
      }
      this.source.disconnect();
      this.source = null;
    }
  }

  private clampPosition(position: number): number {
    if (!Number.isFinite(position)) {
      return 0;
    }
    return Math.min(this.duration, Math.max(0, position));
  }
}

export const createAudioApiPlayerEngine = (): PlayerEngine =>
  new AudioApiPlayerEngine();
