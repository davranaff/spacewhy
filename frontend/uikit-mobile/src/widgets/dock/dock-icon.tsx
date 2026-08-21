import {
  Boxes,
  ChevronDown,
  House,
  LayoutTemplate,
  Music2,
  Palette,
  Pause,
  Play,
  RefreshCw,
  Settings,
  SkipBack,
  SkipForward,
  X,
  type LucideProps,
} from 'lucide-react-native';
import type { ComponentType } from 'react';

import type { DockIconName } from '@/app/navigation/navigation-contracts';

export type DockActionIconName =
  | DockIconName
  | 'close'
  | 'collapse'
  | 'music'
  | 'pause'
  | 'play'
  | 'refresh'
  | 'skip-back'
  | 'skip-forward';

const ICONS: Record<DockActionIconName, ComponentType<LucideProps>> = {
  close: X,
  collapse: ChevronDown,
  components: Boxes,
  home: House,
  layout: LayoutTemplate,
  music: Music2,
  palette: Palette,
  pause: Pause,
  play: Play,
  refresh: RefreshCw,
  settings: Settings,
  'skip-back': SkipBack,
  'skip-forward': SkipForward,
};

type DockIconProps = {
  color: string;
  name: DockActionIconName;
  size?: number;
};

export const DockIcon = ({ color, name, size = 20 }: DockIconProps) => {
  const Glyph = ICONS[name];

  return <Glyph color={color} size={size} strokeWidth={1.75} />;
};
