import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { getDockContentInset } from '@/widgets/dock/dock-layout';
import type { DockMode } from '@/widgets/dock/dock-state';

export const useDockContentInset = (mode: DockMode): number => {
  const insets = useSafeAreaInsets();

  return getDockContentInset(mode, insets.bottom);
};
