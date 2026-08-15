export { PlayerExpandedContent } from '@/features/player/components/player-expanded-content';
export { PlayerMiniContent } from '@/features/player/components/player-mini-content';
export { PLAYER_DEMO_QUEUE } from '@/features/player/data/demo-queue';
export {
  AudioApiPlayerEngine,
  PlayerEngineUnavailableError,
  createAudioApiPlayerEngine,
} from '@/features/player/engine/audio-api-engine';
export { usePlayerDockModel } from '@/features/player/hooks/use-player-dock-model';
export { usePlayerLifecycle } from '@/features/player/hooks/use-player-lifecycle';
export { usePlayerReducedMotion } from '@/features/player/hooks/use-player-reduced-motion';
export { formatPlayerTime } from '@/features/player/lib/format-time';
export { runPlayerCommand } from '@/features/player/lib/run-player-command';
export {
  PlayerController,
  createPlayerController,
  playerController,
} from '@/features/player/lib/player-controller';
export {
  createPlayerStore,
  playerStore,
  selectCurrentTrack,
  selectProgress,
  usePlayerStore,
  type PlayerStoreState,
} from '@/features/player/store/player-store';
export type {
  PlayerDockModel,
  PlayerEngine,
  PlayerEngineFactory,
  PlayerError,
  PlayerErrorCode,
  PlayerSnapshot,
  PlayerStatus,
  PlayerTrack,
} from '@/features/player/types/player.types';
