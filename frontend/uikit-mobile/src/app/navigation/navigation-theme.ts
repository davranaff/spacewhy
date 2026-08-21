import type { Theme } from '@react-navigation/native';

export type NavigationThemeSource = Readonly<{
  mode: 'light' | 'dark';
  colors: Readonly<{
    canvas: string;
    canvasElevated: string;
    text: string;
    border: string;
    accent: string;
    negative: string;
  }>;
}>;

export const createNavigationTheme = (
  source: NavigationThemeSource,
): Theme => ({
  dark: source.mode === 'dark',
  colors: {
    primary: source.colors.accent,
    background: source.colors.canvas,
    card: source.colors.canvasElevated,
    text: source.colors.text,
    border: source.colors.border,
    notification: source.colors.negative,
  },
  fonts: {
    regular: { fontFamily: 'System', fontWeight: '400' },
    medium: { fontFamily: 'System', fontWeight: '500' },
    bold: { fontFamily: 'System', fontWeight: '700' },
    heavy: { fontFamily: 'System', fontWeight: '800' },
  },
});
