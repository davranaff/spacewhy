import type { DockRouteName } from '@/app/navigation/navigation-contracts';

export type DockMode =
  | 'navigation'
  | 'compact'
  | 'contextual'
  | 'mini-player'
  | 'expanded-player';

export type DockState = Readonly<{
  mode: DockMode;
  activeRoute: DockRouteName;
  returnMode: Exclude<DockMode, 'contextual' | 'expanded-player'>;
}>;

export type DockAction =
  | { type: 'route-changed'; route: DockRouteName }
  | { type: 'mode-changed'; mode: DockMode }
  | { type: 'context-dismissed' }
  | { type: 'player-expanded' }
  | { type: 'player-collapsed'; hasTrack: boolean };

export const initialDockState: DockState = {
  mode: 'navigation',
  activeRoute: 'OverviewTab',
  returnMode: 'navigation',
};

const isReturnMode = (
  mode: DockMode,
): mode is Exclude<DockMode, 'contextual' | 'expanded-player'> =>
  mode !== 'contextual' && mode !== 'expanded-player';

export const dockReducer = (
  state: DockState,
  action: DockAction,
): DockState => {
  switch (action.type) {
    case 'route-changed':
      return { ...state, activeRoute: action.route };
    case 'mode-changed':
      return {
        ...state,
        mode: action.mode,
        returnMode: isReturnMode(action.mode) ? action.mode : state.returnMode,
      };
    case 'context-dismissed':
      return { ...state, mode: state.returnMode };
    case 'player-expanded':
      return { ...state, mode: 'expanded-player' };
    case 'player-collapsed':
      return {
        ...state,
        mode: action.hasTrack ? 'mini-player' : state.returnMode,
      };
  }
};
