export type ThemeMode = 'system' | 'light' | 'dark';

export type ResolvedThemeMode = Exclude<ThemeMode, 'system'>;

const sharedTokens = {
  spacing: {
    xxs: 4,
    xs: 8,
    sm: 12,
    md: 16,
    lg: 24,
    xl: 32,
    xxl: 48,
  },
  radius: {
    sm: 12,
    md: 18,
    lg: 24,
    xl: 32,
    pill: 999,
  },
  typography: {
    display: {
      fontSize: 32,
      lineHeight: 38,
      fontWeight: '700' as const,
    },
    title: {
      fontSize: 20,
      lineHeight: 26,
      fontWeight: '700' as const,
    },
    body: {
      fontSize: 16,
      lineHeight: 23,
      fontWeight: '400' as const,
    },
    label: {
      fontSize: 13,
      lineHeight: 18,
      fontWeight: '600' as const,
    },
  },
  motion: {
    instant: 100,
    quick: 180,
    standard: 280,
  },
} as const;

const palettes = {
  dark: {
    canvas: '#050505',
    canvasElevated: '#0B0C0E',
    surface: '#111216',
    surfaceElevated: '#181A1F',
    text: '#F7F7F8',
    textMuted: '#999DA6',
    border: 'rgba(255, 255, 255, 0.16)',
    accent: '#F7F7F8',
    accentContrast: '#050505',
    positive: '#40D886',
    warning: '#FFB020',
    negative: '#FF5A5F',
  },
  light: {
    canvas: '#F4F5F7',
    canvasElevated: '#FFFFFF',
    surface: '#FFFFFF',
    surfaceElevated: '#F9FAFB',
    text: '#111216',
    textMuted: '#626873',
    border: 'rgba(17, 18, 22, 0.14)',
    accent: '#111216',
    accentContrast: '#FFFFFF',
    positive: '#168B54',
    warning: '#A86500',
    negative: '#C9363E',
  },
} as const;

export const themeTokens = {
  ...sharedTokens,
  palettes,
} as const;

export interface AppTheme {
  mode: ResolvedThemeMode;
  isDark: boolean;
  colors: (typeof palettes)[ResolvedThemeMode];
  spacing: typeof sharedTokens.spacing;
  radius: typeof sharedTokens.radius;
  typography: typeof sharedTokens.typography;
  motion: typeof sharedTokens.motion;
}

export function createAppTheme(mode: ResolvedThemeMode): AppTheme {
  return {
    mode,
    isDark: mode === 'dark',
    colors: palettes[mode],
    spacing: sharedTokens.spacing,
    radius: sharedTokens.radius,
    typography: sharedTokens.typography,
    motion: sharedTokens.motion,
  };
}
