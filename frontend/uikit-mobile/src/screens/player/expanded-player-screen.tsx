import { StyleSheet, View } from 'react-native';
import { useNavigation } from '@react-navigation/native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { useAppTheme } from '@/shared/theme';
import { PlayerExpandedContent } from '@/features/player';

export function ExpandedPlayerScreen() {
  const theme = useAppTheme();
  const insets = useSafeAreaInsets();
  const navigation = useNavigation();
  const topOrbStyle = {
    backgroundColor: theme.isDark ? '#302019' : '#FFD8CE',
  };
  const bottomOrbStyle = {
    backgroundColor: theme.isDark ? '#101D28' : '#DCEEFF',
  };

  return (
    <View
      style={[
        styles.screen,
        {
          backgroundColor: theme.colors.canvas,
          paddingTop: Math.max(insets.top, 8),
        },
      ]}
    >
      <View
        pointerEvents="none"
        style={[styles.orb, styles.topOrb, topOrbStyle]}
      />
      <View
        pointerEvents="none"
        style={[styles.orb, styles.bottomOrb, bottomOrbStyle]}
      />
      <PlayerExpandedContent
        onClose={() => navigation.goBack()}
        onCollapse={() => navigation.goBack()}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, overflow: 'hidden' },
  orb: {
    position: 'absolute',
    width: 300,
    height: 300,
    borderRadius: 150,
    opacity: 0.38,
  },
  topOrb: { right: -150, top: -100 },
  bottomOrb: { left: -170, bottom: 30 },
});
