import { Theme, alpha } from '@mui/material/styles';
import { ToggleButtonProps, toggleButtonClasses } from '@mui/material/ToggleButton';

// ----------------------------------------------------------------------

const COLORS = ['primary', 'secondary', 'info', 'success', 'warning', 'error'] as const;

// ----------------------------------------------------------------------

export default function ToggleButton(theme: Theme) {
  const rootStyles = (ownerState: ToggleButtonProps) => {
    const defaultStyle = {
      backgroundColor:
        theme.palette.mode === 'dark'
          ? 'rgba(9,9,12,var(--spacewhy-glass-control-alpha))'
          : 'rgba(255,255,255,var(--spacewhy-glass-control-alpha-light))',
      backdropFilter:
        'blur(var(--spacewhy-glass-control-blur)) saturate(var(--spacewhy-glass-saturation))',
      WebkitBackdropFilter:
        'blur(var(--spacewhy-glass-control-blur)) saturate(var(--spacewhy-glass-saturation))',
      transition: theme.transitions.create(['transform', 'background-color', 'border-color'], {
        duration: 180,
      }),
      '&:active': {
        transform: 'scale(0.97)',
      },
      [`&.${toggleButtonClasses.selected}`]: {
        borderColor: 'currentColor',
        boxShadow: '0 0 0 0.5px currentColor',
      },
    };

    const colorStyle = COLORS.map((color) => ({
      ...(ownerState.color === color && {
        '&:hover': {
          borderColor: alpha(theme.palette[color].main, 0.48),
          backgroundColor: alpha(theme.palette[color].main, theme.palette.action.hoverOpacity),
        },
      }),
    }));

    const disabledState = {
      [`&.${toggleButtonClasses.disabled}`]: {
        [`&.${toggleButtonClasses.selected}`]: {
          color: theme.palette.action.disabled,
          backgroundColor: theme.palette.action.selected,
          borderColor: theme.palette.action.disabledBackground,
        },
      },
    };

    return [defaultStyle, ...colorStyle, disabledState];
  };

  return {
    MuiToggleButton: {
      styleOverrides: {
        root: ({ ownerState }: { ownerState: ToggleButtonProps }) => rootStyles(ownerState),
      },
    },
    MuiToggleButtonGroup: {
      styleOverrides: {
        root: {
          borderRadius: theme.shape.borderRadius,
          backgroundColor:
            theme.palette.mode === 'dark'
              ? 'rgba(9,9,12,var(--spacewhy-glass-control-alpha))'
              : 'rgba(255,255,255,var(--spacewhy-glass-control-alpha-light))',
          backdropFilter:
            'blur(var(--spacewhy-glass-control-blur)) saturate(var(--spacewhy-glass-saturation))',
          WebkitBackdropFilter:
            'blur(var(--spacewhy-glass-control-blur)) saturate(var(--spacewhy-glass-saturation))',
          border: `solid 1px ${alpha(theme.palette.grey[500], 0.08)}`,
        },
        grouped: {
          margin: 4,
          [`&.${toggleButtonClasses.selected}`]: {
            boxShadow: 'none',
          },
          '&:not(:first-of-type), &:not(:last-of-type)': {
            borderRadius: theme.shape.borderRadius,
            borderColor: 'transparent',
          },
        },
      },
    },
  };
}
