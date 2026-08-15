import {
  DOCK_EDGE_GAP,
  getDockContentInset,
  getPlayerAwareDockContentInset,
  getDockSurfaceHeight,
} from '../../src/widgets/dock/dock-layout';

describe('dock layout contracts', () => {
  it('reserves content space for every supported mode', () => {
    const modes = [
      'navigation',
      'compact',
      'contextual',
      'mini-player',
      'expanded-player',
    ] as const;

    modes.forEach(mode => {
      expect(getDockContentInset(mode, 34)).toBeGreaterThan(
        getDockSurfaceHeight(mode),
      );
    });
  });

  it('uses a minimum gesture-bar gap when the safe area is zero', () => {
    expect(getDockContentInset('navigation', 0)).toBe(
      getDockSurfaceHeight('navigation') + DOCK_EDGE_GAP + 12,
    );
  });

  it('never shrinks the expanded player below the mini player', () => {
    expect(getDockSurfaceHeight('expanded-player')).toBeGreaterThan(
      getDockSurfaceHeight('mini-player'),
    );
  });

  it('adds the mini player without charging the system safe area twice', () => {
    expect(getPlayerAwareDockContentInset(34, true)).toBe(
      getDockContentInset('navigation', 34) +
        getDockContentInset('mini-player', 0),
    );
    expect(getPlayerAwareDockContentInset(34, false)).toBe(
      getDockContentInset('navigation', 34),
    );
  });
});
