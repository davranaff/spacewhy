import { createNavigationTheme } from '../../src/app/navigation/navigation-theme';

const source = {
  mode: 'dark' as const,
  colors: {
    accent: '#ffffff',
    canvas: '#000000',
    canvasElevated: '#111111',
    border: '#333333',
    negative: '#ff453a',
    text: '#f5f5f7',
  },
};

describe('createNavigationTheme', () => {
  it('maps semantic Spacewhy tokens to React Navigation roles', () => {
    expect(createNavigationTheme(source)).toMatchObject({
      dark: true,
      colors: {
        primary: source.colors.accent,
        background: source.colors.canvas,
        card: source.colors.canvasElevated,
        text: source.colors.text,
        border: source.colors.border,
        notification: source.colors.negative,
      },
    });
  });

  it('derives light mode without changing semantic colors', () => {
    const light = createNavigationTheme({ ...source, mode: 'light' });

    expect(light.dark).toBe(false);
    expect(light.colors).toEqual(createNavigationTheme(source).colors);
  });
});
