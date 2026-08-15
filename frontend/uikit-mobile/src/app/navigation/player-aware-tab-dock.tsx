import { useMemo } from 'react';
import { View, type ImageSourcePropType } from 'react-native';
import type { BottomTabBarProps } from '@react-navigation/bottom-tabs';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { openExpandedPlayer } from '@/app/navigation/navigation-ref';
import { usePlayerDockModel } from '@/features/player';
import { TabDock } from '@/widgets/dock';
import { MiniPlayerDock } from '@/widgets/mini-player';

export const PlayerAwareTabDock = (props: BottomTabBarProps) => {
  const insets = useSafeAreaInsets();
  const player = usePlayerDockModel();
  const artwork = useMemo<ImageSourcePropType | undefined>(
    () => (player.artworkUri ? { uri: player.artworkUri } : undefined),
    [player.artworkUri],
  );
  const showMiniPlayer = player.hasTrack && player.status !== 'idle';

  return (
    <View pointerEvents="box-none">
      {showMiniPlayer ? (
        <MiniPlayerDock
          artwork={artwork}
          bottomSafeArea={0}
          onClose={player.onClose}
          onNext={player.onNext}
          onPrevious={player.onPrevious}
          onRetry={player.onRetry}
          onToggleExpanded={() => {
            openExpandedPlayer();
          }}
          onTogglePlayback={player.onTogglePlayback}
          progress={player.progress}
          status={player.status}
          subtitle={player.subtitle}
          title={player.title}
        />
      ) : null}
      <TabDock {...props} bottomSafeArea={insets.bottom} />
    </View>
  );
};
