export type PlayerStatus =
  | 'empty'
  | 'idle'
  | 'loading'
  | 'playing'
  | 'paused'
  | 'error'
  | 'unavailable';

export type PlayerErrorCode =
  | 'engine-unavailable'
  | 'load-failed'
  | 'playback-failed';

export type PlayerTrack = Readonly<{
  id: string;
  title: string;
  artist: string;
  source: string;
  artworkUri?: string;
}>;

export type PlayerError = Readonly<{
  code: PlayerErrorCode;
  message: string;
}>;

export type PlayerSnapshot = Readonly<{
  queue: readonly PlayerTrack[];
  currentIndex: number;
  status: PlayerStatus;
  position: number;
  duration: number;
  error: PlayerError | null;
}>;

export interface PlayerEngine {
  load(track: PlayerTrack, onEnded: () => void): Promise<number>;
  play(offsetSeconds: number): Promise<void>;
  pause(): Promise<number>;
  seek(offsetSeconds: number, continuePlaying: boolean): Promise<void>;
  getPosition(): number;
  dispose(): Promise<void>;
}

export type PlayerEngineFactory = () => PlayerEngine;

export type PlayerDockModel = Readonly<{
  hasTrack: boolean;
  title: string;
  subtitle?: string;
  artworkUri?: string;
  progress: number;
  status: 'idle' | 'loading' | 'playing' | 'paused' | 'error';
  onTogglePlayback: () => void;
  onClose: () => void;
  onRetry: () => void;
  onPrevious: () => void;
  onNext: () => void;
}>;
