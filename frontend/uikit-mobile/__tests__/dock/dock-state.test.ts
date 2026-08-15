import {
  dockReducer,
  initialDockState,
} from '../../src/widgets/dock/dock-state';

describe('dockReducer', () => {
  it('tracks the active route without changing the mode', () => {
    const next = dockReducer(initialDockState, {
      type: 'route-changed',
      route: 'ComponentsTab',
    });

    expect(next).toEqual({
      ...initialDockState,
      activeRoute: 'ComponentsTab',
    });
  });

  it.each(['navigation', 'compact', 'mini-player'] as const)(
    'remembers %s as a stable return mode',
    mode => {
      const next = dockReducer(initialDockState, {
        type: 'mode-changed',
        mode,
      });

      expect(next.mode).toBe(mode);
      expect(next.returnMode).toBe(mode);
    },
  );

  it('returns to the prior stable mode after contextual actions', () => {
    const compact = dockReducer(initialDockState, {
      type: 'mode-changed',
      mode: 'compact',
    });
    const contextual = dockReducer(compact, {
      type: 'mode-changed',
      mode: 'contextual',
    });

    expect(contextual.returnMode).toBe('compact');
    expect(dockReducer(contextual, { type: 'context-dismissed' }).mode).toBe(
      'compact',
    );
  });

  it('collapses an expanded player to the right state', () => {
    const expanded = dockReducer(initialDockState, { type: 'player-expanded' });

    expect(
      dockReducer(expanded, { type: 'player-collapsed', hasTrack: true }).mode,
    ).toBe('mini-player');
    expect(
      dockReducer(expanded, { type: 'player-collapsed', hasTrack: false }).mode,
    ).toBe('navigation');
  });
});
