import { alpha, Theme } from '@mui/material/styles';
import { ButtonProps, buttonClasses } from '@mui/material/Button';

// ----------------------------------------------------------------------

const COLORS = ['primary', 'secondary', 'info', 'success', 'warning', 'error'] as const;

// NEW VARIANT
declare module '@mui/material/Button' {
  interface ButtonPropsVariantOverrides {
    soft: true;
  }
}

// ----------------------------------------------------------------------

export default function Button(theme: Theme) {
  const isLight = theme.palette.mode === 'light';

  const rootStyles = (ownerState: ButtonProps) => {
    const inheritColor = ownerState.color === 'inherit';

    const containedVariant = ownerState.variant === 'contained';

    const outlinedVariant = ownerState.variant === 'outlined';

    const textVariant = ownerState.variant === 'text';

    const softVariant = ownerState.variant === 'soft';

    const smallSize = ownerState.size === 'small';

    const mediumSize = ownerState.size === 'medium';

    const largeSize = ownerState.size === 'large';

    const defaultStyle = {
      position: 'relative' as const,
      overflow: 'hidden',
      borderRadius: 'calc(var(--spacewhy-glass-radius) * 0.72)',
      border: isLight
        ? '1px solid rgba(18,24,33,var(--spacewhy-glass-edge-alpha-light))'
        : '1px solid rgba(255,255,255,var(--spacewhy-glass-edge-alpha-dark))',
      backgroundColor: isLight
        ? 'rgba(255,255,255,var(--spacewhy-glass-control-alpha-light))'
        : 'rgba(9,9,12,var(--spacewhy-glass-control-alpha))',
      backdropFilter:
        'blur(var(--spacewhy-glass-control-blur)) saturate(var(--spacewhy-glass-saturation))',
      WebkitBackdropFilter:
        'blur(var(--spacewhy-glass-control-blur)) saturate(var(--spacewhy-glass-saturation))',
      boxShadow: isLight
        ? '0 7px 20px rgba(26,32,44,var(--spacewhy-glass-shadow-alpha-light))'
        : '0 8px 22px rgba(0,0,0,var(--spacewhy-glass-shadow-alpha-dark))',
      transform: 'translateY(0) scale(1)',
      transition: theme.transitions.create(['transform', 'border-color'], {
        duration: 160,
        easing: 'cubic-bezier(0.2, 0.8, 0.2, 1)',
      }),
      '@media (hover: hover) and (pointer: fine)': {
        '&:hover': {
          transform: 'translateY(-1px) scale(1.01)',
          borderColor: isLight ? 'rgba(18,24,33,0.18)' : 'rgba(255,255,255,0.20)',
        },
      },
      '&:active': {
        transform: 'translateY(0) scale(0.975)',
      },
      ...(inheritColor && {
        // CONTAINED
        ...(containedVariant && {
          color: isLight ? theme.palette.common.white : theme.palette.grey[800],
          backgroundColor: isLight ? theme.palette.grey[800] : theme.palette.common.white,
          backgroundImage: 'none',
          '&:hover': {
            backgroundColor: isLight ? theme.palette.grey[700] : theme.palette.grey[400],
          },
        }),
        // OUTLINED
        ...(outlinedVariant && {
          backgroundColor: isLight
            ? 'rgba(255,255,255,var(--spacewhy-glass-control-alpha-light))'
            : 'rgba(9,9,12,var(--spacewhy-glass-control-alpha))',
          '&:hover': {
            backgroundColor: isLight ? 'rgba(255,255,255,0.72)' : 'rgba(20,20,24,0.54)',
          },
        }),
        // TEXT
        ...(textVariant && {
          borderColor: 'transparent',
          boxShadow: 'none',
          backgroundColor: 'transparent',
          backdropFilter: 'none',
          WebkitBackdropFilter: 'none',
          '&:hover': {
            backgroundColor: theme.palette.action.hover,
          },
        }),
        // SOFT
        ...(softVariant && {
          color: theme.palette.text.primary,
          backgroundColor: alpha(theme.palette.grey[500], 0.08),
          '&:hover': {
            backgroundColor: alpha(theme.palette.grey[500], 0.24),
          },
        }),
      }),
      ...(outlinedVariant && {
        '&:hover': {
          borderColor: 'currentColor',
          boxShadow: '0 0 0 0.5px currentColor',
        },
      }),
    };

    const colorStyle = COLORS.map((color) => ({
      ...(ownerState.color === color && {
        // CONTAINED
        ...(containedVariant && {
          '&:hover': {
            boxShadow: theme.customShadows[color],
          },
        }),
        // SOFT
        ...(softVariant && {
          color: theme.palette[color][isLight ? 'dark' : 'light'],
          backgroundColor: alpha(theme.palette[color].main, 0.16),
          '&:hover': {
            backgroundColor: alpha(theme.palette[color].main, 0.32),
          },
        }),
      }),
    }));

    const disabledState = {
      [`&.${buttonClasses.disabled}`]: {
        // SOFT
        ...(softVariant && {
          backgroundColor: theme.palette.action.disabledBackground,
        }),
      },
    };

    const size = {
      ...(smallSize && {
        height: 30,
        fontSize: 13,
        paddingLeft: 8,
        paddingRight: 8,
        ...(textVariant && {
          paddingLeft: 4,
          paddingRight: 4,
        }),
      }),
      ...(mediumSize && {
        paddingLeft: 12,
        paddingRight: 12,
        ...(textVariant && {
          paddingLeft: 8,
          paddingRight: 8,
        }),
      }),
      ...(largeSize && {
        height: 48,
        fontSize: 15,
        paddingLeft: 16,
        paddingRight: 16,
        ...(textVariant && {
          paddingLeft: 10,
          paddingRight: 10,
        }),
      }),
    };

    return [defaultStyle, ...colorStyle, disabledState, size];
  };

  return {
    MuiButton: {
      defaultProps: {
        color: 'inherit',
        disableElevation: true,
      },

      styleOverrides: {
        root: ({ ownerState }: { ownerState: ButtonProps }) => rootStyles(ownerState),
      },
    },
  };
}
