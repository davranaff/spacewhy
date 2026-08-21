import { useEffect } from 'react';
import { AppState } from 'react-native';

import { playerController } from '@/features/player/lib/player-controller';
import { runPlayerCommand } from '@/features/player/lib/run-player-command';

/** Mount once near the application shell so playback pauses safely off-screen. */
export function usePlayerLifecycle(): void {
  useEffect(() => {
    const subscription = AppState.addEventListener('change', state => {
      if (state !== 'active') {
        runPlayerCommand(playerController.handleBackground());
      }
    });

    return () => {
      subscription.remove();
      runPlayerCommand(
        playerController
          .handleBackground()
          .then(() => playerController.dispose()),
      );
    };
  }, []);
}
