import { useMemo } from 'react';

import { playerController } from '@/features/player/lib/player-controller';
import { runPlayerCommand } from '@/features/player/lib/run-player-command';
import {
  selectCurrentTrack,
  selectProgress,
  usePlayerStore,
} from '@/features/player/store/player-store';
import type { PlayerDockModel } from '@/features/player/types/player.types';

export function usePlayerDockModel(): PlayerDockModel {
  const track = usePlayerStore(selectCurrentTrack);
  const progress = usePlayerStore(selectProgress);
  const status = usePlayerStore(state => state.status);

  return useMemo(
    () => ({
      hasTrack: Boolean(track),
      title: track?.title ?? 'No track selected',
      subtitle: track?.artist,
      artworkUri: track?.artworkUri,
      progress,
      status:
        status === 'empty'
          ? 'idle'
          : status === 'unavailable'
          ? 'error'
          : status,
      onTogglePlayback: () =>
        runPlayerCommand(playerController.togglePlayback()),
      onClose: () => runPlayerCommand(playerController.close()),
      onRetry: () => runPlayerCommand(playerController.retry()),
      onPrevious: () => runPlayerCommand(playerController.previous()),
      onNext: () => runPlayerCommand(playerController.next()),
    }),
    [progress, status, track],
  );
}
